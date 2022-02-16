from twelvedata import TDClient
import time, json, os, yaml
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from waveshare_epd import epd2in7

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')

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

def updateDisplay(pricestack):
    pricenow = pricestack[-1]
    sparkbitmap = Image.open(os.path.join(picdir,'spark.bmp'))
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
    image = Image.new('L', (264,176), 255)    # 255: clear the image with white
    draw = ImageDraw.Draw(image)
    draw.text((110,90),str(days_ago)+" day : "+pricechange,font =font_date,fill = 0)
    writewrappedlines(image, pricestring,50,55,8,15,"Roboto-Medium" )
    image.paste(sparkbitmap,(80,40))
    draw.text((95,15),timestamp,font =font_date,fill = 0)
#   Return the ticker image
    return image

def display_image(img):
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    epd.display_4Gray(epd.getbuffer_4Gray(img))
    epd.sleep()
    return

with open(configfile) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
symbollist=currencystringtolist(config['ticker']['currency'])
fiatcurrency=config['ticker']['fiatcurrency']
timezone=config['ticker']['timezone']
refreshtime=float(config['ticker']['refreshtime'])/60
apikey=config['api']['apikey']
datapoints=20*24

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
    image=updateDisplay(flipit)
    display_image(image)
    time.sleep(refreshtime)
