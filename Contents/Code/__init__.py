import re, random

PREFIX          = "/video/hulu" 

TITLE           = 'Hulu'
ART             = 'art-default.jpg'
ICON_DEFAULT    = 'icon-default.png'
ICON_SEARCH     = 'icon-search.png'
ICON_PREFS      = 'icon-prefs.png'

URL_LISTINGS    = 'http://www.hulu.com/browse/search?keyword=&alphabet=All&family_friendly=0&closed_captioned=0&channel=%s&subchannel=&network=All&display=%s&decade=All&type=%s&view_as_thumbnail=true&block_num=%s'
SEASON_LISTINGS = 'http://www.hulu.com/videos/slider?classic_sort=asc&items_per_page=%d&page=%d&season=%d&show_id=%s&show_placeholders=1&sort=original_premiere_date&type=episode'

REGEX_CHANNEL_LISTINGS    = Regex('Element.replace\("channel", "(.+)\);')
REGEX_SHOW_LISTINGS       = Regex('Element.update\("show_list", "(.+)\);')
REGEX_RATING_FEED         = Regex('Rating: ([^ ]+) .+')
REGEX_TV_EPISODE_FEED     = Regex('(?P<show>[^-]+) - s(?P<season>[0-9]+) \| e(?P<episode>[0-9]+) - (?P<title>.+)$')

NAMESPACES      = {'activity': 'http://activitystrea.ms/spec/1.0/',
                   'media': 'http://search.yahoo.com/mrss/'}

CACHE_INTERVAL  = 3600

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(PREFIX, MainMenu, TITLE, ICON_DEFAULT, ART)
  Plugin.AddViewGroup('InfoList', viewMode = 'InfoList', mediaType = 'items')
  Plugin.AddViewGroup('List', viewMode = 'List', mediaType = 'items')

  ObjectContainer.title1 = TITLE
  ObjectContainer.art = R(ART)
  ObjectContainer.view_group = 'List'

  DirectoryObject.thumb = R(ICON_DEFAULT)
  DirectoryObject.art = R(ART)
  
  VideoClipObject.thumb = R(ICON_DEFAULT)
  VideoClipObject.art = R(ART)

  HTTP.CacheTime = CACHE_INTERVAL

  loginResult = HuluLogin()
  Log("Login success: " + str(loginResult))
        
####################################################################################################  
def HuluLogin():

  username = Prefs["email"]
  password = Prefs["password"]

  if (username != None) and (password != None):
    authentication_url = "https://secure.hulu.com/account/authenticate?" + str(int(random.random()*1000000000))
    authentication_headers = {"Cookie": "sli=1; login=" + username + "; password=" + password + ";"}
    resp = HTTP.Request(authentication_url, headers = authentication_headers, cacheTime=0).content
    
    if resp == "Login.onComplete();":
      HTTP.Headers['Cookie'] = HTTP.CookiesForURL('https://secure.hulu.com/')
      for item in HTTP.CookiesForURL('https://secure.hulu.com/').split(';'):
        if '_hulu_uid' in item :
          Dict['_hulu_uid'] = item[11:]
      return True
    else:
      return False
  else:
    return False
        
####################################################################################################
def MainMenu():
  oc = ObjectContainer()
  oc.add(DirectoryObject(key = Callback(MyHulu, title = "My Hulu"), title = "My Hulu"))
  oc.add(DirectoryObject(key = Callback(Channels, title = "TV", item_type = "tv", display = "Shows%20with%20full%20episodes%20only"), title = "TV"))
  oc.add(DirectoryObject(key = Callback(Channels, title = "Movies", item_type = "movies", display = "Full%20length%20movies%20only"), title = "Movies"))
  oc.add(DirectoryObject(key = Callback(MostPopular, title = "Popular Videos"), title = "Popular Videos"))
  oc.add(DirectoryObject(key = Callback(MostRecent, title = "Recently Added"), title = "Recently Added"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Highest Rated Videos", feed_url = "http://www.hulu.com/feed/highest_rated/videos"), title = "Highest Rated Videos"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Soon-to-Expire Videos", feed_url = "http://www.hulu.com/feed/expiring/videos"), title = "Soon-to-Expire Videos"))
  oc.add(SearchDirectoryObject(identifier="com.plexapp.search.hulu", title = "Search...", prompt = "Search for Videos", thumb = R(ICON_SEARCH)))
  return oc

####################################################################################################
def MyHulu(title):

  # Attempt to login
  loginResult = HuluLogin()  
  Log("MyHulu Login success: " + str(loginResult))

  if loginResult:
    oc = ObjectContainer()
  else:
    oc = MessageContainer("User info required", "Please enter your Hulu email address and password in Preferences.")
  return oc
  
####################################################################################################
def Channels(title, item_type, display):
  oc = ObjectContainer(title2 = title)

  channels_page = HTTP.Request(URL_LISTINGS % ("All", display, item_type, 0)).content
  html_content = REGEX_CHANNEL_LISTINGS.findall(channels_page)[0].decode('unicode_escape')
  html_page = HTML.ElementFromString(html_content)

  for genre in html_page.xpath('//div[@class="cbx-options"]//li'):
    channel = genre.get('value')
    oc.add(DirectoryObject(
      key = Callback(ListShows, title = channel, channel = channel, item_type = item_type, display = display),
      title = channel))

  return oc

####################################################################################################
def MostPopular(title):
  oc = ObjectContainer(title2 = title)
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos Today", feed_url = "http://www.hulu.com/feed/popular/videos/today"), title = "Popular Videos Today"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos This Week", feed_url = "http://www.hulu.com/feed/popular/videos/this_week"), title = "Popular Videos This Week"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos This Month", feed_url = "http://www.hulu.com/feed/popular/videos/this_month"), title = "Popular Videos This Month"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Popular Videos of All Time", feed_url = "http://www.hulu.com/feed/popular/videos/all_time"), title = "Popular Videos of All Time"))
  return oc

####################################################################################################
def MostRecent(title):
  oc = ObjectContainer(title2 = title)
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Shows", feed_url = "http://www.hulu.com/feed/recent/shows"), title = "Recently Added Shows"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Movies", feed_url = "http://www.hulu.com/feed/recent/movies"), title = "Recently Added Movies"))
  oc.add(DirectoryObject(key = Callback(Feeds, title = "Recently Added Videos", feed_url = "http://www.hulu.com/feed/recent/videos"), title = "Recently Added Videos"))
  return oc

####################################################################################################
def Feeds(title, feed_url):
  oc = ObjectContainer(title2 = title)

  feed = XML.ElementFromURL(feed_url)
  for item in feed.xpath('//channel/item'):
    url = item.xpath('.//link/text()')[0]
    thumb = item.xpath('.//media:thumbnail', namespaces = NAMESPACES)[0].get('url')
    date = Datetime.ParseDate(item.xpath('.//pubDate/text()')[0])

    summary_text = item.xpath('.//description/text()')[0]
    summary_node = HTML.ElementFromString(summary_text)
    summary = summary_node.xpath('.//p/text()')[0]
 
    rating = None
    try: rating = float(REGEX_RATING_FEED.findall(summary_text)[0]) * 2
    except: pass

    title = item.xpath('.//title/text()')[0]
    try:

      # A feed will normally contain individual episodes. Their titles are of formats similar to the following:
      #    The Voice - s2 | e15 - Quarterfinals: Live Eliminations
      # If we detect this, then we can extract the available information. If this fails, then we will simply 
      # fallback to a normal VideoClipObject
      details = REGEX_TV_EPISODE_FEED.match(title).groupdict()

      oc.add(EpisodeObject(
        url = url,
        title = details['title'],
        summary = summary,
        show = details['show'],
        season = int(details['season']),
        index = int(details['episode']),
        thumb = thumb,
        originally_available_at = date,
        rating = rating))
    except:

      oc.add(VideoClipObject(
        url = url,
        title = title,
        summary = summary,
        thumb = thumb,
        originally_available_at = date,
        rating = rating))

  return oc

####################################################################################################
def ListShows(title, channel, item_type, display):
  oc = ObjectContainer()

  shows_page = HTTP.Request(URL_LISTINGS % (channel, display, item_type, 0)).content
  html_content = REGEX_SHOW_LISTINGS.findall(shows_page)[0].decode('unicode_escape')
  html_page = HTML.ElementFromString(html_content)

  for item in html_page.xpath('//a[@class = "info_hover"]'):
    original_url = item.get('href').split('?')[0]
    info_url = original_url.replace('http://www.hulu.com/', 'http://www.hulu.com/shows/info/')
    details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})

    if details.has_key('films_count'):
      oc.add(MovieObject(
        url = original_url,
        title = details['name'],
        summary = details['description'],
        thumb = details['thumbnail_url'],
        tags = [ tag['tag_name'] for tag in details['taggings'] ],
        originally_available_at = Datetime.ParseDate(details['film_date'])))

    elif details.has_key('episodes_count') and details['episodes_count'] > 0:

      oc.add(TVShowObject(
        key = Callback(ListSeasons, title = details['name'], show_url = original_url, info_url = info_url, show_id = details['id']),
        rating_key = original_url,
        title = details['name'],
        summary = details['description'],
        thumb = details['thumbnail_url'],
        episode_count = details['episodes_count'],
        viewed_episode_count = 0,
        tags = [ tag['tag_name'] for tag in details['taggings'] ]))

  return oc

####################################################################################################
def ListSeasons(title, show_url, info_url, show_id):
  oc = ObjectContainer(title2 = title)

  show_page = HTML.ElementFromURL(show_url)
  details = JSON.ObjectFromURL(info_url, headers = {'X-Requested-With': 'XMLHttpRequest'})

  for season in show_page.xpath('//div[contains(@class, "season-filter")]/ul/li/text()'):
    if season == 'All':
      continue

    season_number = int(season)
    oc.add(SeasonObject(
      key = Callback(ListEpisodes, title = details['name'], show_id = details['id'], season = season_number),
      rating_key = show_url,
      title = details['name'],
      index = season_number,
      summary = details['description'],
      thumb = details['thumbnail_url']))

  return oc

####################################################################################################
def ListEpisodes(title, show_id, season):
  return ObjectContainer(title2 = title)