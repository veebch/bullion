from twelvedata import TDClient
import time, json, os, yaml, textwrap
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from PIL import ImageFont
from PIL import ImageDraw
from waveshare_epd import epd2in7
from babel import Locale
from babel.numbers import decimal, format_currency, format_scientific

dirname = os.path.dirname(__file__)
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
font_date = ImageFont.truetype(os.path.join(fontdir,'PixelSplitter-Bold.ttf'),11)

def currencystringtolist(currstring):
    # Takes the string for currencies in the config.yaml file and turns it into a list
    curr_list = currstring.split(",")
    curr_list = [x.strip(' ') for x in curr_list]
    return curr_list

def makeSpark(pricestack):
    # Draw and save the sparkline that represents historical data
    # Subtract the mean from the sparkline to make the mean appear on the plot (it's really the x axis)
    themean= sum(pricestack)/float(len(pricestack))
    x = [xx - themean for xx in pricestack]
    fig, ax = plt.subplots(1,1,figsize=(10,4))
    plt.plot(x, color='0', linewidth=4)
    plt.plot(len(x)-1, x[-1], color='.4', marker='o')
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

def thumbnailtype(symbol):
    if symbol in ['XAG','XAU','XPT','XPD','XG']:
        typethumbnail= 'bullion.bmp'
    elif symbol in ['BTC','ETH','XRP','LTC','BNB','BCH']:
        typethumbnail= symbol+'.bmp'
    else:
        typethumbnail='default.bmp'
    typefilename = os.path.join(picdir,typethumbnail)
    typeimage = Image.open(typefilename).convert("RGBA")
    resize = 80,80
    typeimage.thumbnail(resize, Image.ANTIALIAS)
    return typeimage

def updateDisplay(pricestack,fiat,symbolnow):
    pricenow = pricestack[-1]
    sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))

    typeimage = thumbnailtype(symbolnow)

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
    if pricenow > 10000:
        # round to nearest whole unit of currency, this is an ugly hack for now
        pricestring=custom_format_currency(int(pricenow), fiat.upper(), localetag)
    else:
        pricestring = format_currency(pricenow, fiat.upper(),locale=localetag, decimal_quantization=True)
    image = Image.new('L', (264,176), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    draw.text((120,100),"1 day : "+pricechange,font =font_date,fill = 0)
    draw.line((0,116,264,116), fill=128, width=1)
    writewrappedlines(image, pricestring,50,53,8,15,"Roboto-Medium" )
    image.paste(typeimage, (10,10))
    image.paste(sparkbitmap,(90,30))
    fontreduction=30-(len(symbolnow)-3)*5 # longer symbol, smaller font
    _place_text(image,symbolnow,-80,10,fontreduction,"Roboto-Medium",0)
    draw.text((95,15),timestamp,font =font_date,fill = 0)
#   Return the ticker image
    return image

def _place_text(img, text, x_offset=0, y_offset=0,fontsize=40,fontstring="Forum-Regular", fill=0):
    '''
    Put some centered text at a location on the image.
    '''
    draw = ImageDraw.Draw(img)
    try:
        filename = os.path.join(dirname, './fonts/'+fontstring+'.ttf')
        font = ImageFont.truetype(filename, fontsize)
    except OSError:
        font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', fontsize)
    img_width, img_height = img.size
    text_width, _ = font.getsize(text)
    text_height = fontsize
    draw_x = (img_width - text_width)//2 + x_offset
    draw_y = (img_height - text_height)//2 + y_offset
    draw.text((draw_x, draw_y), text, font=font,fill=fill )

def writewrappedlines(img,text,fontsize=16,y_text=20,height=15, width=25,fontstring="Roboto-Medium"):
    lines = textwrap.wrap(text, width)
    numoflines=0
    for line in lines:
        _place_text(img, line,0, y_text, fontsize,fontstring)
        y_text += height
        numoflines+=1
    return img

def custom_format_currency(value, currency, locale):
    value = decimal.Decimal(value)
    locale = Locale.parse(locale)
    pattern = locale.currency_formats['standard']
    force_frac = ((0, 0) if value == int(value) else None)
    return pattern.apply(value, locale, currency=currency, force_frac=force_frac)

def display_image(img, inverted):
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    if inverted:
        #PIL doesnt like to invert binary images, so convert to RGB, invert and then convert back to RGBA
        img = ImageOps.invert( img.convert('RGB') )
        img = img.convert('RGBA')
    epd.display_4Gray(epd.getbuffer_4Gray(img))
    epd.sleep()
    return

with open(configfile) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
symbollist=currencystringtolist(config['ticker']['currency'])
fiatcurrency=config['ticker']['fiatcurrency']
timezone=config['ticker']['timezone']
refreshtime=float(config['ticker']['refreshtime'])
apikey=config['api']['apikey']
datapoints=20*24

try:
    while True:
        for symbolnow in symbollist:
            fullsymbol=symbolnow+'/'+fiatcurrency
            print(fullsymbol)
            td = TDClient(apikey=apikey)
            # Construct the necessary time series
            ts = td.time_series(
                symbol=fullsymbol,
                interval="5min",
                outputsize=datapoints,
                timezone=timezone,
            )

            csvts = ts.as_json()
            pricestack=[]
            for i in range(1,datapoints):
                pricestack.append(float(csvts[i]['close']))
            flipit=pricestack[::-1]
            makeSpark(flipit)
            image=updateDisplay(flipit,fiatcurrency,symbolnow)
            display_image(image,config['display']['inverted'])
            time.sleep(refreshtime)
except IOError as e:
        print(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
except IOError as e:
        print(str(e)+" Line: "+str(e.__traceback__.tb_lineno))
except KeyboardInterrupt:
        print('Keyboard Interrupt')

