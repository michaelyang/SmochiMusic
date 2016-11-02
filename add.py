#!/usr/bin/python
#-*- coding:utf-8 -*-

import os
import re
import csv
import sys
import codecs
import platform
import datetime
import pymysql.cursors
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import media, posts, taxonomies

if (platform.system() == 'Windows'):
	artistPath = 'C:\\Users\\Michael\\Sync\\Artists'
else:
	artistPath = '/Users/myang/Sync/Artists'
wp_url = 'http://www.smochimusic.com/xmlrpc.php'
wp_username = 'yangmike'
wp_password = 'Mxbi9gf8n'
wp = Client(wp_url,wp_username,wp_password)
mediaLibrary = wp.call(media.GetMediaLibrary({}))
connection = pymysql.connect(host='smochimusic.com',
                             user='smochimu_wp153',
                             password='mxbi9gf8n',
                             db='smochimu_wp153',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

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

def getCheckList():
    with connection.cursor() as cursor:
        sql = 'SELECT artist, album, song FROM upload_info WHERE published = 1'
		cursor.execute(sql)
		return list(cursor.fetchall())
	
def getPostSlugList():
	postSlugList = []
	offset = 0
	increment = 20
	while True:
		postList = wp.call(posts.GetPosts({'post_type': 'download','number': increment, 'offset': offset}))
		if len(postList) == 0:
			break
		for post in postList:
			postSlugList.append(post.slug)
		offset = offset + increment
	return postSlugList

#Returns: [String] Slug
#postType should be 'single' or 'bundle'
def getSlug(postType, albumType, artist, album, song):
	if postType == 'single':
		return (albumType + '-' + re.sub('[!|(|)|.|,]','',artist) + '-' + re.sub('[!|(|)|.|,]','',song)).replace(' ','-').lower()
	else:
		return (albumType + '-album' + '-' + re.sub('[!|(|)|.|,]','',artist) + '-' + re.sub('[!|(|)|.|,]','',album)).replace(' ','-').lower()

def getInfo(artist, album):
	infoPath = os.path.join(artistPath,artist,'Albums',album,'info.txt')
	with codecs.open(infoPath, encoding='utf-8') as info:
		albumType = info.readline().strip()
		releaseDate = info.readline().strip()
	return str(albumType), str(releaseDate)

#Check if media is already uploaded on WP
#YES: return url to image
#NO: Upload image, return url to image
def uploadArtwork(artist, album):
	imagePath = os.path.join(artistPath,artist,'Albums',album,'cover.jpg')
	name = (re.sub('[!|(|)|.|,]','',artist) + '-' + re.sub('[!|(|)|.|,]','',album)).replace(' ','-') + '.jpg'
	for item in mediaLibrary:
		if (str(item.title) == name):
			print ('Image for ' + name + ' already exists')
			return item.id
	data = {
			'name': name,
			'type': 'image/jpeg'
			}
	with open(imagePath, 'rb') as img:
		data['bits'] = xmlrpc_client.Binary(img.read())
	response = wp.call(media.UploadFile(data))
	return response['id']

#Combines two text files to make an html with formatting
def getContent(artist, album, song):
	lyricsPath = os.path.join(artistPath,artist,'Albums',album,song,'lyrics.txt')
	translationPath = os.path.join(artistPath,artist,'Albums',album,song,'translation.txt')
	if not os.path.exists(lyricsPath):
		print ('Warning: No Lyrics for %s - %s' % (artist, song))
		return ''	
	content = '&nbsp;<div class="left" style="text-align: center; font-family: "Nanum Gothic"; font-size: 13px;">'	
	with codecs.open(lyricsPath, encoding='utf-8') as lyrics:
		content = content + lyrics.read()
	content = content + '</div><div class="right" style="text-align: center; font-size: 14px;">'
	with codecs.open(translationPath, encoding='utf-8') as translation:
		content = content + translation.read()
	content = content + '</div>&nbsp;'
	return content

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

def uploadPost(postType, artist, album, song, artwork):
	albumType, releaseDate = getInfo(artist,album)
	post = WordPressPost()
	post.post_type = 'download'
	if postType == 'bundle':
		post.title = album
	else:
		post.title = song
		post.content = getContent(artist, album, song)
	post.date = datetime.datetime.strptime(releaseDate, '%Y.%m.%d')
	#post.slug = getSlug(postType, albumType, artist, album, song)
	post.terms = wp.call(taxonomies.GetTerms('download_artist', {'search' : artist}))
	post.thumbnail = artwork
	post.custom_fields = []
	post.post_status = 'draft'
	post.custom_fields.append({
	        'key': 'year',
	        'value': releaseDate
	})
	post.id = wp.call(posts.NewPost(post))
	try:
		with connection.cursor() as cursor:
		sql = "INSERT INTO `users` (`email`, `password`) VALUES (%s, %s)"
		cursor.execute(sql, ('webmaster@python.org', 'very-secret'))
    connection.commit()
	if postType == 'bundle':
		print ('Upload Successful for album %s - %s. Post id = %s' % (artist, album, post.id))
	else:
		print ('Upload Successful for song %s - %s. Post id = %s' % (artist, song, post.id))
	return
'''
wpPosts = wp.call(posts.GetPosts({'post_type': 'download','number':3}))
for post in wpPosts:
	print (post)
	print ('id: ' + post.id)
	print (post.slug)
	print (post.post_status)
	print ('title: ' + post.title)
	print (utf_translate(post.content))
	print (utf_translate(post.excerpt))
	print (type(post.terms))
	for custom_field in post.custom_fields:
		print (custom_field)
	print (post.thumbnail)
	#wp.call(posts.EditPost('1566',post))
'''
def main():
	#postSlugList = getPostSlugList()
	artistList = getArtistList()
	for artist in artistList:
		print ('Artist Name: ' + artist + '\n')
		albumList = getAlbumList(artist)
		for album in albumList:
			artwork = uploadArtwork(artist, album)
			#uploadPost('bundle', artist, album, '', artwork)
			songList = getSongList(artist, album)
			for song in songList:
				pass
				#uploadPost('single', artist, album, song, artwork)
	finally:
		connection.close()

if __name__ == "__main__":
	main()


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



