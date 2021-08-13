import sys, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import os, requests, re, json
from urllib.parse import urlencode, quote_plus, parse_qsl, quote, unquote
import pickle
import random
from datetime import datetime
import time

addon           = xbmcaddon.Addon(id='plugin.video.bjjfanatics')
addon_url       = sys.argv[0]
addon_handle    = int(sys.argv[1])
addon_icon      = addon.getAddonInfo('icon')
addon_BASE_PATH = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

TOKEN_FILE = xbmcvfs.translatePath(os.path.join('special://temp','bjjfanatics_token.txt'))


urls = {
        "all_instructionals" : "https://members.bjjfanatics.com/api/v1/ordersShopify.json",
        "specific_instructional" : "https://members.bjjfanatics.com/api/v1/get_product.json",
        "login_address" : "https://members.bjjfanatics.com/api/v1/shopify_login.json"   
        }

headers = {
          "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
          "accept": "application/json, text/plain, */*",
          "sec-fetch-mode": "cors",
          "accept-encoding": "gzip, deflate, br",
          "accept-language": "en-AU,en;q=0.9",
          "content-type": "application/json;charset=UTF-8",
          "sec-fetch-dest": "empty",
          "sec-fetch-site": "same-origin",
          "Origin" : "https://members.bjjfanatics.com"
         }


def kodi_print(text_to_print):
    """print to kodi.log the line lnumber and the text"""
    
    if not isinstance(text_to_print, str):
        text_to_print = str(text_to_print)

    xbmc.log("{0}".format(text_to_print),level=xbmc.LOGERROR)
    return



def get_creds():
    """Get username and password. Return dict of username and password"""

    if len(addon.getSetting('username')) == 0 or len(addon.getSetting('password')) == 0:
        return None

    return {
        'email': addon.getSetting('username'),
        'password': addon.getSetting('password')
    }

def get_user_id():
    """Take in the credentials as dict['email', 'password'] and return the customer id in dict"""
    
    

    credentials = get_creds()

    payload = { "search": "","search_inselects": "", "email": credentials['email'], "password": credentials['password']}



    session = requests.Session()
    #session.headers = headers
    response = session.post(urls["login_address"], headers=headers, data=json.dumps(payload))
    session.close()
    info_dict = response.json()
    
    if response.status_code == 200:
        token = {"customer_id" :info_dict['customers'][0]['id']}
        return token
    else:
        kodi_print("could no get auth token: " + str(info_dict))

        return False


def get_token():
    """Get the token either from the file saved or by getting a new one if the file doesn't exist"""
    
    if not os.path.isfile(TOKEN_FILE): #if bearer token file does not exist
        token = get_user_id()
        
        with open(TOKEN_FILE, 'wb') as handle:
            pickle.dump(token, handle, protocol=pickle.HIGHEST_PROTOCOL)
            ## Replace by above pickle.dump(open(TOKEN_FILE, mode='wb'))  ###THIS was added new, not sure why this wasn't here before?
    else:
        with open(TOKEN_FILE, 'rb') as handle:
            token = pickle.load(handle)
        ## replaced by above token = pickle.load(open(TOKEN_FILE), mode='rb')
    return token


def post_request(url,payload):
    session = requests.Session()
    response = session.post(url, headers=headers,data=json.dumps(payload))

    if response.status_code < 400:
        return  response.json()

def get_instructionals_for_menu():
    """Get data for your owned instructionals and put it into an array for menu build"""
    my_id = get_token()
    instructional_data = post_request(urls['all_instructionals'], my_id)

    instructional_menu_array = []
    
    for item in instructional_data:
        try:
            menu_item = {
                'id' : item['id'],
                'name' : item['name'],
                'customer_id' : item['shopify_user_id'],
                'front_cover' : item['image'][-1],
                'back_cover' : item['image'][-2],
                'description' : item['description'],
                'tags' : item.get('tags'),
                'instructor' : item.get('instructor'),
                'category_tags' : item.get('category_tags'),
                'type' : 'listing'
            }
        except:
            menu_item = {
                'id' : item['id'],
                'name' : item['name'],
                'customer_id' : item['shopify_user_id'],
                'front_cover' : item['image'][-1],
                'back_cover' : item['image'][-1],
                'description' : item['description'],
                'tags' : item.get('tags'),
                'instructor' : item.get('instructor'),
                'category_tags' : item.get('category_tags'),
                'type' : 'listing'
            }        
           
        instructional_menu_array.append(menu_item)
    
    return instructional_menu_array


def make_titles_shorter(array_of_dict):
    """See if titles in array of dict have too long"""

    def keep_last_three(string):
        my_pattern = '.*?(\S+\s\S+\s\S+$)'
        my_group = re.match(my_pattern, string)
        try:
            return my_group.group(1)
        except:
            return string
    
    my_array_of_names = []
    
    for item in array_of_dict:
        item['title'] = keep_last_three(item['title'])
        
        my_array_of_names.append(item)
    
    
    return my_array_of_names



def build_product_menu(user_id,product_id):
    """Build a list for use in the xbmc menu. This is at the Individual instructional level level"""
    
    
    payload_for_product = {'product_id': product_id, 'shopify_user_id': user_id}
    #get the data from the web call
    product_data = post_request(urls['specific_instructional'],payload_for_product)
    
    
    my_return_items = []
    
    #kodi_print(product_data['image'])
    
    #video_data = product_data['videos']  #Swapped for bellow line
    video_data = make_titles_shorter(product_data['videos'] )
    
    put_pickle_product_data(video_data,product_data['id']) #put the data into a file for later use
    
    for item in video_data:
        
        item_dict = {
            'name': item['title'],
            'id_video' : item['id'],
            'product_id' : product_data['id'],
            'front_cover' : item['image'],
            'back_cover' : item['image'],
            'duration' : item['duration'],
            'description' : product_data['description'],
            'customer_id' : payload_for_product['shopify_user_id'],
            'category_tags' : product_data['category_tags'],
            'tagline' : product_data['category_tags'],
            'plotoutline' : product_data['instructor'],
            'type' : 'instructional_videos'
        }
        my_return_items.append(item_dict)
    
    return my_return_items


def put_pickle_product_data(product_data_video, product_id):
    """Add the data for the entire instructional (product_data['videos']) to a pickle container. 
    Name the pickle file the product id"""
    
    filename = xbmcvfs.translatePath(os.path.join('special://temp', 'bjjfan' + str(product_id) + '.txt'))
    
    with open(filename, 'wb') as handle:
        pickle.dump(product_data_video, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    return True
    
def get_pickle_product_data(product_id):
    """Read in the pickle data file <product_id>, and video_id and return a list of items,
    that contain the name and timestamp"""
    
    filename = xbmcvfs.translatePath(os.path.join('special://temp', 'bjjfan' + str(product_id) + '.txt'))
    
    with open(filename, 'rb') as handle:
        my_data = pickle.load(handle)
        
    
    return my_data


def build_video_menu(customer_id, id_video, product_id):
    """Take in customer id and id of the id_video and product id"""
    
    video_data = get_pickle_product_data(product_id)
    
    
    
    for item in video_data:
        if str(item ["id"]) == str(id_video):
            the_video_list = item
            break
    
    all_list = []
    for video_item in the_video_list['contents']:
        video_snip_data = {
            'name' : video_item['name_content'] + " " + video_item['minute_video'][1:],
            'timestamp' : convert_time_to_seconds(video_item['minute_video']),
            'url' : the_video_list['url'],
            'picture' : the_video_list['image'],
            'customer_id' : customer_id,
            'type' : 'video'
        }
        all_list.append(video_snip_data)
        
        
    return all_list
    
        
def convert_time_to_seconds_a(datestring):
    #kodi_print(datestring)
    
    my_datetime = datetime.strptime("00:00:00",'%H:%M:%S')
    
    pt = datetime.strptime(datestring,'%H:%M:%S')
    total_seconds = pt.second + pt.minute*60 + pt.hour*3600 

    return total_seconds
    
def convert_time_to_seconds(datestring):
    #kodi_print(datestring)
    pt = time.strptime(datestring,'%H:%M:%S')
    total_seconds = pt.tm_sec + pt.tm_min*60 + pt.tm_hour *3600
    
    
    
    return str(total_seconds)    
    
    

def build_menu(itemData):     
    """ Takes in array of dict, using this array builds a menu to display in Kodi"""
    
    episode = 1
    
    for my_item in itemData:
        
        
        if my_item["type"] == "video":
            kodi_item = xbmcgui.ListItem(label=my_item["name"],label2=my_item["name"])
            kodi_item.setArt({  'thumb': my_item["picture"], 
                                'icon' :  my_item["picture"], 
                                'landscape': my_item["picture"], 
                                'poster' : my_item["picture"], 
                                'banner': my_item["picture"], 
                                'fanart': my_item["picture"]})

            video_info = {
                            'plot': my_item.get("name"),
                            'plotoutline' : my_item.get("name"),
                            'tagline' : my_item.get("name"),
                            'setoverview' : my_item.get("name"),
                            'episodeguide' : my_item.get("name"),
                            'mediatype' : "tvshow",
                            'episode' : episode
                           }
            episode = episode +1

            kodi_item.setInfo(type='video', infoLabels=video_info)
                                
            url = '{0}?action=play&url={1}&uid={2}&tit={3}&time={4}'.format(addon_url, my_item['url'],my_item['customer_id'],quote(my_item["name"]),my_item["timestamp"] ) ##added encode utf
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=False, totalItems=len(itemData)) ###last false is if it is a directory
        
        elif my_item["type"] == 'listing':
            kodi_item = xbmcgui.ListItem(label=my_item.get("name"))
            kodi_item.setArt({  'thumb': my_item.get("front_cover"), 
                                'icon' :  my_item.get("front_cover"), 
                                'landscape': my_item.get("back_cover"), 
                                'poster' : my_item.get("front_cover"), 
                                'banner': my_item.get("back_cover"), 
                                'fanart': my_item.get("back_cover")})
            video_info = {
                            'plot': my_item.get("description"),
                            'plotoutline' : my_item.get("instructor"),
                            'tagline' : my_item.get("tags"),
                            'setoverview' : my_item.get("category_tags"),
                            'mediatype' : "tvshow",
                            'duration': my_item.get("duration")
                           }
            kodi_item.setInfo(type='video', infoLabels=video_info)
            url = '{0}?action={1}&uid={2}&pid={3}'.format(addon_url, my_item['type'], my_item['customer_id'], my_item['id'])
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=True, totalItems=len(itemData)) ###last false is if it is a directory 
            
        elif my_item["type"] == 'instructional_videos':
            kodi_item = xbmcgui.ListItem(label=my_item.get("name"))
            #kodi_print(my_item)
            kodi_item.setArt({  'thumb': my_item.get("front_cover"), 
                                'icon' :  my_item.get("front_cover"), 
                                'landscape': my_item.get("back_cover"), 
                                'poster' : my_item.get("back_cover"), 
                                'banner': my_item.get("back_cover"), 
                                'fanart': my_item.get("back_cover")})
            video_info = {
                            'plot': my_item.get("description"),
                            'plotoutline' : my_item.get("instructor"),
                            'tagline' : my_item.get("tags"),
                            'setoverview' : my_item.get("category_tags"),
                            'mediatype' : "tvshow",
                            'duration': my_item.get("duration")
                           }
            kodi_item.setInfo(type='video', infoLabels=video_info)
            url = '{0}?action={1}&uid={2}&vid={3}&pid={4}'.format(addon_url, 'instructional', my_item['customer_id'], my_item['id_video'], my_item['product_id'])
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, isFolder=True, totalItems=len(itemData)) ###last false is if it is a directory 



    ###Thats it create the folder structure
    xbmcplugin.endOfDirectory(addon_handle)



def play_video(url, uid, tit, startpos):
    
    
    #tag = xbmc.Player().getVideoInfoTag()
    video_to_play  = xbmc.Player()
    
    #video_to_play.setVideoStream(url)
    video_to_play.play(url)
    video_to_play.pause()
    video_to_play.seekTime(int(startpos))
    video_to_play.pause()
    
    
    #playitem = xbmcgui.ListItem(path=url,label=tit)
    #playitem.setContentLookup(False)
    #playitem.setProperty('isFolder', 'false')
    #playitem.setProperty('IsPlayable', 'true')
    #playitem.setProperty('StartOffset', startpos)
    
    #return xbmcplugin.setResolvedUrl(addon_handle, True, playitem)
    
    
    #xbmc.Player().play(url,  playitem)

    #xbmc.Player().seektime(startpos)    


    

def router(paramstring):
    """Router for kodi to select the menu item and route appropriately. """ 
    params = dict(parse_qsl(paramstring))
    
    if params:
        action = params['action']
        if action == 'listing':
            menu_data = build_product_menu(params['uid'],params['pid'])
            build_menu(menu_data)
        
        elif action == 'instructional':
            menu_data = build_video_menu(params['uid'],params['vid'],params['pid'] ) 
            build_menu(menu_data)
            
        
        elif action == 'play':
            play_video(params['url'],params['uid'],params['tit'], params['time'])
    
        else:
            pass
    else:
        menu_data = get_instructionals_for_menu()
        build_menu(menu_data)


       

if __name__ == '__main__':     
    router(sys.argv[2][1:])

