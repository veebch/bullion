#!/usr/bin/python3
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
import currency
import os
import sys
import logging
from waveshare_epd import epd2in7
import time
import requests
import urllib, json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import yaml
import socket
import textwrap
import argparse
from babel import Locale
from babel.numbers import decimal, format_currency, format_scientific

dirname = os.path.dirname(__file__)
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
font_date = ImageFont.truetype(os.path.join(fontdir,'PixelSplitter-Bold.ttf'),11)
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

def internet(hostname="google.com"):
    """
    Host: google.com
    """
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname(hostname)
        # connect to the host -- tells us if the host is actually
        # reachable
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except:
        logging.info("Google says No")
        time.sleep(1)
    return False

def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

def _place_text(img, text, x_offset=0, y_offset=0,fontsize=40,fontstring="Forum-Regular", fill=0):
    '''
    Put some centered text at a location on the image.
    '''
    draw = ImageDraw.Draw(img)
    try:
        filename = os.path.join(dirname, './fonts/googlefonts/'+fontstring+'.ttf')
        font = ImageFont.truetype(filename, fontsize)
    except OSError:
        font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', fontsize)
    img_width, img_height = img.size
    text_width, _ = font.getsize(text)
    text_height = fontsize
    draw_x = (img_width - text_width)//2 + x_offset
    draw_y = (img_height - text_height)//2 + y_offset
    draw.text((draw_x, draw_y), text, font=font,fill=fill )

def writewrappedlines(img,text,fontsize=16,y_text=20,height=15, width=25,fontstring="Roboto-Light"):
    lines = textwrap.wrap(text, width)
    numoflines=0
    for line in lines:
        _place_text(img, line,0, y_text, fontsize,fontstring)
        y_text += height
        numoflines+=1
    return img


def getData(config,other):
    sleep_time = 10
    num_retries = 5
    whichcoin,fiat=configtocoinandfiat(config)
    logging.info("Getting Data")
    timeseriesstack = []
    for x in range(0, num_retries):
        prices, connectfail=  getprices()
        if connectfail==True:
            pass
        else:
            # Do stuff with the data you got
            timeseriesstack = prices
        if connectfail==True:
            message="Trying again in ", sleep_time, " seconds"
            logging.warn(message)
            time.sleep(sleep_time)  # wait before trying to fetch the data again
            sleep_time *= 2  # exponential backoff
        else:
            break
    return timeseriesstack

def beanaproblem(message):
#   A visual cue that the wheels have fallen off
    thebean = Image.open(os.path.join(picdir,'thebean.bmp'))
    image = Image.new('L', (264, 176), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    image.paste(thebean, (60,45))
    draw.text((95,15),str(time.strftime("%-H:%M %p, %-d %b %Y")),font =font_date,fill = 0)
    writewrappedlines(image, "Issue: "+message)
    return image

def makeSpark(pricestack):
    # Draw and save the sparkline that represents historical data
    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)
    themean= sum(pricestack)/float(len(pricestack))
    x = [xx - themean for xx in pricestack]
    fig, ax = plt.subplots(1,1,figsize=(10,3))
    plt.plot(x, color='k', linewidth=6)
    plt.plot(len(x)-1, x[-1], color='r', marker='o')
    # Remove the Y axis
    for k,v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(c='k', linewidth=4, linestyle=(0, (5, 2, 1, 2)))
    # Save the resulting bmp file to the images directory
    plt.savefig(os.path.join(picdir,'spark.png'), dpi=17)
    imgspk = Image.open(os.path.join(picdir,'spark.png'))
    file_out = os.path.join(picdir,'spark.bmp')
    imgspk.save(file_out)
    plt.close(fig)
    plt.cla() # Close plot to prevent memory error
    ax.cla() # Close axis to prevent memory error
    imgspk.close()
    return

def custom_format_currency(value, currency, locale):
    value = decimal.Decimal(value)
    locale = Locale.parse(locale)
    pattern = locale.currency_formats['standard']
    force_frac = ((0, 0) if value == int(value) else None)
    return pattern.apply(value, locale, currency=currency, force_frac=force_frac)


def updateDisplay(config,pricestack,other):
    """
    Takes the price data, the desired coin/fiat combo along with the config info for formatting
    if config is re-written following adustment we could avoid passing the last two arguments as
    they will just be the first two items of their string in config
    """
    with open(configfile) as f:
        originalconfig = yaml.load(f, Loader=yaml.FullLoader)
    originalcoin=originalconfig['ticker']['currency']
    originalcoin_list = originalcoin.split(",")
    originalcoin_list = [x.strip(' ') for x in originalcoin_list]
    whichcoin,fiat=configtocoinandfiat(config)
    days_ago=int(config['ticker']['sparklinedays'])
    pricenow = pricestack[-1]
    if config['display']['inverted'] == True:
        currencythumbnail= 'currency/'+whichcoin+'INV.bmp'
    else:
        currencythumbnail= 'currency/'+whichcoin+'.bmp'
    tokenfilename = os.path.join(picdir,currencythumbnail)
    sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))
    ATHbitmap= Image.open(os.path.join(picdir,'ATH.bmp'))
#   Check for token image, if there isn't one, get on off coingecko, resize it and pop it on a white background
    if os.path.isfile(tokenfilename):
        logging.debug("Getting token Image from Image directory")
        tokenimage = Image.open(tokenfilename).convert("RGBA")
    else:
        logging.debug("Getting token Image from Coingecko")
        tokenimageurl = "https://api.coingecko.com/api/v3/coins/"+whichcoin+"?tickers=false&market_data=false&community_data=false&developer_data=false&sparkline=false"
        rawimage = requests.get(tokenimageurl, headers=headers).json()
        tokenimage = Image.open(requests.get(rawimage['image']['large'], headers = headers, stream=True).raw).convert("RGBA")
        resize = 100,100
        tokenimage.thumbnail(resize, Image.ANTIALIAS)
        # If inverted is true, invert the token symbol before placing if on the white BG so that it is uninverted at the end - this will make things more
        # legible on a black display
        if config['display']['inverted'] == True:
            #PIL doesnt like to invert binary images, so convert to RGB, invert and then convert back to RGBA
            tokenimage = ImageOps.invert( tokenimage.convert('RGB') )
            tokenimage = tokenimage.convert('RGBA')
        new_image = Image.new("RGBA", (120,120), "WHITE") # Create a white rgba background with a 10 pixel border
        new_image.paste(tokenimage, (10, 10), tokenimage)
        tokenimage=new_image
        tokenimage.thumbnail((100,100),Image.ANTIALIAS)
        tokenimage.save(tokenfilename)
    pricechangeraw = round((pricestack[-1]-pricestack[0])/pricestack[-1]*100,2)
    if pricechangeraw >= 10:
        pricechange = str("%+d" % pricechangeraw)+"%"
    else:
        pricechange = str("%+.2f" % pricechangeraw)+"%"
    if '24h' in config['display'] and config['display']['24h']:
        timestamp= str(time.strftime("%-H:%M, %d %b %Y"))
    else:
        timestamp= str(time.strftime("%-I:%M %p, %d %b %Y"))
    # This is where a locale change can be made
    localetag = 'en_US' # This is a way of forcing the locale currency info eg 'de_DE' for German formatting
    fontreduce=0 # This is an adjustment that needs to be applied to coins with very low fiat value per coin
    if pricenow > 10000:
        # round to nearest whole unit of currency, this is an ugly hack for now
        pricestring=custom_format_currency(int(pricenow), fiat.upper(), localetag)
    elif pricenow >.01:
        pricestring = format_currency(pricenow, fiat.upper(),locale=localetag, decimal_quantization=False)
    else:
        # looks like you have a coin with a tiny value per coin, drop the font size, not ideal but better than just printing SHITCOIN
        pricestring = format_currency(pricenow, fiat.upper(),locale=localetag, decimal_quantization=False)
        fontreduce=15
    image = Image.new('L', (264,176), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    if other['ATH']==True:
        image.paste(ATHbitmap,(205,85))
    draw.text((110,90),str(days_ago)+" day : "+pricechange,font =font_date,fill = 0)
    if 'showvolume' in config['display'] and config['display']['showvolume']:
        draw.text((110,105),"24h vol : " + human_format(other['volume']),font =font_date,fill = 0)
    writewrappedlines(image, pricestring,50-fontreduce,55,8,15,"Roboto-Medium" )
    image.paste(sparkbitmap,(80,40))
    image.paste(tokenimage, (0,10))
    draw.text((95,15),timestamp,font =font_date,fill = 0)
    if config['display']['orientation'] == 270 :
        image=image.rotate(180, expand=True)
#   If the display is inverted, invert the image usinng ImageOps
    if config['display']['inverted'] == True:
        image = ImageOps.invert(image)
#   Return the ticker image
    return image

def currencystringtolist(currstring):
    # Takes the string for currencies in the config.yaml file and turns it into a list
    curr_list = currstring.split(",")
    curr_list = [x.strip(' ') for x in curr_list]
    return curr_list

def currencycycle(curr_string):
    curr_list=currencystringtolist(curr_string)
    # Rotate the array of currencies from config.... [a b c] becomes [b c a]
    curr_list = curr_list[1:]+curr_list[:1]
    return curr_list

def display_image(img):
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    epd.display_4Gray(epd.getbuffer_4Gray(img))
    epd.sleep()
    thekeys=initkeys()
#   Have to remove and add key events to make them work again
    removekeyevent(thekeys)
    addkeyevent(thekeys)
    return

def fullupdate(config,lastcoinfetch):
    """
    The steps required for a full update of the display
    Earlier versions of the code didn't grab new data for some operations
    but the e-Paper is too slow to bother the coingecko API
    """
    other={}
    try:
        pricestack= getData(config)
        # generate sparkline
        makeSpark(pricestack)
        # update display
        image=updateDisplay(config, pricestack)
        display_image(image)
        lastgrab=time.time()
        time.sleep(0.2)
    except Exception as e:
        message="Data pull/print problem"
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image)
        time.sleep(20)
        lastgrab=lastcoinfetch
    return lastgrab

def configtocoinandfiat(config):
    asset_list = currencystringtolist(config['ticker']['currency'])
    fiat_list=currencystringtolist(config['ticker']['fiatcurrency'])
    currency=asset_list[0]
    fiat=fiat_list[0]
    return currency, fiat

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default='info', help='Set the log level (default: info)')
    args = parser.parse_args()

    loglevel = getattr(logging, args.log.upper(), logging.WARN)
    logging.basicConfig(level=loglevel)
    # Set timezone based on ip address
    try:
        os.system("sudo /home/pi/.local/bin/tzupdate")
    except:
        logging.info("Timezone Not Set")
    try:
        logging.info("epd2in7 BTC Frame")
#       Get the configuration from config.yaml
        with open(configfile) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        logging.info(config)
        config['display']['orientation']=int(config['display']['orientation'])
        staticcoins=config['ticker']['currency']
#       Note how many coins in original config file
        howmanycoins=len(config['ticker']['currency'].split(","))
#       Note that there has been no data pull yet
        datapulled=False
#       Time of start
        lastcoinfetch = time.time()
#       Quick Sanity check on update frequency, waveshare says no faster than 180 seconds, but we'll make 60 the lower limit
        if float(config['ticker']['updatefrequency'])<60:
            logging.info("Throttling update frequency to 60 seconds")
            updatefrequency=60.0
        else:
            updatefrequency=float(config['ticker']['updatefrequency'])
        while internet() ==False:
            logging.info("Waiting for internet")
        while True:
            if (time.time() - lastcoinfetch > updatefrequency) or (datapulled==False):
                if config['display']['cycle']==True and (datapulled==True):
                    asset_list = currencycycle(config['ticker']['currency'])
                    config['ticker']['currency']=",".join(asset_list)
                lastcoinfetch=fullupdate(config,lastcoinfetch)
                datapulled = True
#           Reduces CPU load during that while loop
            time.sleep(0.01)
    except IOError as e:
        logging.error(e)
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image)
    except Exception as e:
        logging.error(e)
        image=beanaproblem(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
        display_image(image)  
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        image=beanaproblem("Keyboard Interrupt")
        display_image(image)
        epd2in7.epdconfig.module_exit()
        exit()

if __name__ == '__main__':
    main()
