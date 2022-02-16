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

def updateDisplay(config, pricestack):
    pass

def display_image():
    epd = epd2in7.EPD()
    epd.Init_4Gray()
    epd.display_4Gray(epd.getbuffer_4Gray(img))
    epd.sleep()
    thekeys=initkeys()
#   Have to remove and add key events to make them work again
    removekeyevent(thekeys)
    addkeyevent(thekeys)
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
    image=updateDisplay(config, flipit)
    display_image(image)
    time.sleep(refreshtime)
