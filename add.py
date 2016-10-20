#!/usr/bin/python
#-*- coding:utf-8 -*-

import os
import re
import csv
import sys
import codecs
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import media, posts

#artistPath = '/Users/myang/Sync/Artists'
artistPath = 'C:\\Users\\Michael\\Sync\\Artists'
#destinationFile = '/Users/myang/Sync/test.csv'
destinationFile = 'C:\\Users\\Michael\\Sync\\test.csv'
wp_url = 'http://www.smochimusic.com/xmlrpc.php'
wp_username = 'yangmike'
wp_password = 'Mxbi9gf8n'

wp = Client(wp_url,wp_username,wp_password)
mediaLibrary = wp.call(media.GetMediaLibrary({}))

#Connect to mysql
def check(artist,album):
	return true

#Returns: [List] List of artists in Sync path
def getArtistList():
	rootdir = artistPath
	return [name for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

#Returns: [List] List of albums for a given artist
def getAlbumList(artist):
	rootdir = os.path.join(artistPath,artist,'Albums')
	return [name for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

#Returns: [List] List of songs for a given artist, album pair
def getSongList(artist, album):
	rootdir = os.path.join(artistPath,artist,'Albums',album)
	return [name for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

#Returns: [String] Slug
#postType should be 'single' or 'bundle'
def getSlug(postType, artist, album):
	infoPath = os.path.join(artistPath,artist,'Albums',album,'info.txt')
	if 'single' in open(infoPath).read():
		albumType = 'single'
	else:
		albumType = 'full'
	if postType == 'single':
		prefix = albumType
	else:
		prefix = albumType + '-album'
	return (prefix + '-' + re.sub('[!|(|)|.|,]','',artist) + '-' + re.sub('[!|(|)|.|,]','',album)).replace(' ','-').lower()

#Check if media is already uploaded on WP
#YES: return url to image
#NO: Upload image, return url to image
def getArtwork(artist, album):
	imagePath = os.path.join(artistPath,artist,'Albums',album,'cover.jpg')
	name = (re.sub('[!|(|)|.|,]','',artist) + '-' + re.sub('[!|(|)|.|,]','',album)).replace(' ','-') + '.jpg'
	for item in mediaLibrary:
		if (item.title == name):
			print ('Image for ' + name + ' already exists')
			return item.link
	data = {
			'name': name,
			'type': 'image/jpeg'
			}
	with open(imagePath, 'rb') as img:
		data['bits'] = xmlrpc_client.Binary(img.read())
	response = wp.call(media.UploadFile(data))
	return response['url']

#Combines two text files to make an html with formatting
def getLyricsTranslation(artist, album, song):
	content = '&nbsp;div class="left" style="text-align: center; font-family: "Nanum Gothic"; font-size: 13px;">'
	lyricsPath = os.path.join(artistPath,artist,'Albums',album,song,'lyrics.txt')
	translationPath = os.path.join(artistPath,artist,'Albums',album,song,'translation.txt')
	with codecs.open(lyricsPath, encoding='utf-8') as lyrics:
		print(lyrics.read())
	with open(translationPath, 'r') as translation:
		print(translation.read())
	return content
	'''
	&nbsp;	
	<div class="left" style="text-align: center; font-family: 'Nanum Gothic'; font-size: 13px;">
	<center><b>
	#korean artist - korean title
	</b></center>
	#lyrics
	</div>
	<div class="right" style="text-align: center; font-size: 14px;">
	<center><b>
	#english artist - english title
	</b></center>
	#translation
	</div>
	&nbsp;
	'''
	return

def utf_translate(in_string):
    in_string = in_string.encode('utf-8').decode('utf-8')
    #print in_string
    common_bad_guys={u'—':u'-',#MDASH
    u'"':u'"',#stupid double left quote
    u'"':u'"',#stupid double right quote
    u''':u"'",#stupid left quote
    u''':u"'",#stupid right quote
    u'–':u'-',#NDASH?
    u'…':u'...',#ellipsis
    u'‐':u'-',#NOT SURE
    u'‒':u'-',#also NOT SURE
    u'©':u'&copy;',#copyright symbol,
    u'®':u'&reg;',#registered symbol
    u'�':u'?',#weird ?
    u'™':u'&#8482;',
    u'"':u'\\\"',
    u"'":u"\\\'",
    u'·':u'-',
    u'\u2019':u"'",
    u'\u2018':u"'",
    u"'":u"'",
    u"'":u"'",
    u"\u2026":u'...',
    u'\u201d':u'"'
    }
    for key in common_bad_guys:
        in_string = in_string.replace(key,common_bad_guys[key])
    return in_string

#generateCSV using all of the info above
def getCSV():
	try:
		os.remove(destinationFile)
		print('File removed!')
	except OSError:
		print ('File doesn\'t exist!')
	f = open(destinationFile, 'wt')
	try:
		writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
		writer.writerow( ('Title 1', 'Title 2', 'Title 3') )
		for i in range(10):
			writer.writerow( (i+1, chr(ord('a') + i), '08/%02d/07' % (i+1)) )
	finally:
		f.close()

	return
######################################################

artistList = getArtistList()
for artist in artistList:
	print ('Artist Name: ' + artist + '\n')
	albumList = getAlbumList(artist)
	for album in albumList:
		print ('Album Name: ' + album)
		print (getSlug('bundle',artist,album))
		print (getArtwork(artist,album))
		songList = getSongList(artist, album)
		for song in songList:
			print ('Album Name: ' + album)
			print (getSlug('single',artist,album))
			print (getArtwork(artist,album))
			print (getLyricsTranslation(artist,album,song))

print ('This is it for the artists')
'''
for media in mediaLibrary:
	print (media.id)
	print (len(media.title))
	print (utf_translate(media.title))

getCSV()
'''
'''		1. create a csv that only contains default fields supported by EDD
		2. create another script that goes through all these shit to set piklist fields?
		mysql
		wp9r_postmeta <<piklistshit <<if picklist has their own shit to help us edit this less hackily
		3. post id = object_id in wp9r_term_relationship, need to match artist id with song id (each artist is a term, use wordpress funcs to relate post to a term (aritst))
		4. Scarper for melon << lmao
		5. use jenny to translate
		6. ????
		7. profit
		'''


