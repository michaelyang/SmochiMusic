#!/usr/local/bin/python3
#-*- coding:utf-8 -*-

import os
import re
import csv
import sys
import codecs
import platform
import datetime
import pymysql.cursors
import phpserialize
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
	return [ensureUtf(name) for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

#Returns: [List] List of albums for a given artist
def getAlbumList(artist):
	rootdir = os.path.join(artistPath,artist,'Albums')
#	return ['CC (Campus Couple)']
	return [ensureUtf(name) for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

#Returns: [List] List of songs for a given artist, album pair
def getSongList(artist, album):
	rootdir = os.path.join(artistPath,artist,'Albums',album)
	return [ensureUtf(name) for name in os.listdir(rootdir) if os.path.isdir(os.path.join(rootdir,name))]

def getCheckList():
	with connection.cursor() as cursor:
		sql = 'SELECT item_type, artist, album, song FROM upload_info WHERE published = 1'
		cursor.execute(sql)
		return list(cursor.fetchall())

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
		if (ensureUtf(item.title) == name):
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
	namePath = os.path.join(artistPath,artist,'Albums',album,song,'name.txt')
	lyricsPath = os.path.join(artistPath,artist,'Albums',album,song,'lyrics.txt')
	translationPath = os.path.join(artistPath,artist,'Albums',album,song,'translation.txt')
	lyricsLineCount = 0
	translationLineCount = 0
	if not os.path.exists(namePath):
		print ('Warning: No Name for %s - %s' % (artist, song))
		koreanName = ''
	else:
		with codecs.open(namePath, encoding='utf-8') as names:
			koreanName = names.readline().strip()
			englishName = names.readline().strip()
	if not os.path.exists(lyricsPath):
		print ('Warning: No Lyrics for %s - %s' % (artist, song))
		return '', koreanName
	content = '<div style="text-align: center;"><div style="text-align: center; "Nanum Gothic"; 13px;" class="leftLyrics"><h2>'+ koreanName + '</h2><pre>'
	with codecs.open(lyricsPath, encoding='utf-8') as lyrics:
		content = content + lyrics.read()
		lyricsLineCount++
	content = content + '</pre></div><div style="text-align: center; 14px;" class="rightLyrics"><h2>'+ englishName + '</h2><pre>'
	with codecs.open(translationPath, encoding='utf-8') as translation:
		content = content + translation.read()
		translationLineCount++
	content = content + '</pre></div></div>'
	if (lyricsLineCount != translationLineCount):
		print ('The line numbers don\'t match up for ' + artist + ' ' + album + ' ' + song)
	return content, koreanName

def ensureUtf(s):
  try:
      if type(s) == unicode:
        return s.encode('utf-8')
  except: 
    return str(s)

def uploadPost(postType, artist, album, song, artwork):
	albumType, releaseDate = getInfo(artist,album)
	post = WordPressPost()
	post.post_type = 'download'
	if postType == 'bundle':
		post.title = album
	else:
		post.title = song
		post.content, keyword = getContent(artist, album, song)
	post.date = datetime.datetime.strptime(releaseDate, '%Y.%m.%d')
	post.terms = wp.call(taxonomies.GetTerms('download_artist', {'search' : artist}))
	post.thumbnail = artwork
	post.custom_fields = []
	post.post_status = 'publish'
	post.custom_fields.append({
	        'key': 'year',
	        'value': releaseDate
	})
	post.custom_fields.append({
	        'key': 'music_type',
	        'value': postType
	})
	post.id = wp.call(posts.NewPost(post))
	with connection.cursor() as cursor:
		if postType == 'bundle':
			sql = 'INSERT INTO `upload_info` (`item_type`, `album_type`, `artist`, `album`, `post_title`, `release_date`, `thumbnail_id`, `post_id`, `published`, `updated_at`) VALUES (%s, %s, %s,%s,%s,%s,%s,%s,%s, now())'
			cursor.execute(sql, (postType,albumType,artist,album,post.title,post.date,post.thumbnail,post.id,'1'))
		else:
			sql1 = 'INSERT INTO `upload_info` (`item_type`, `album_type`, `artist`, `album`, `song`, `post_title`, `release_date`, `thumbnail_id`, `post_id`, `published`, `updated_at`) VALUES (%s, %s, %s,%s,%s,%s,%s,%s,%s,%s, now())'
			sql2 = 'INSERT INTO `wp9r_postmeta` (`post_id`, `meta_key`, `meta_value`) VALUES (%s, "_yoast_wpseo_focuskw_text_input", %s)'
			sql3 = 'INSERT INTO `wp9r_postmeta` (`post_id`, `meta_key`, `meta_value`) VALUES (%s, "_yoast_wpseo_focuskw", %s)'
			cursor.execute(sql1, (postType,albumType,artist,album, song,post.title,post.date,post.thumbnail,post.id,'1'))
			cursor.execute(sql2, (post.id, keyword))
			cursor.execute(sql3, (post.id, keyword))
		connection.commit()
	if postType == 'bundle':
		print ('Upload Successful for album %s - %s. Post id = %s' % (artist, album, post.id))
	else:
		print ('Upload Successful for song %s - %s. Post id = %s' % (artist, song, post.id))
	return post.id

def main():
	#postSlugList = getPostSlugList()
	checkList = getCheckList()
	artistList = getArtistList()
	albumArray = ['']
	albumSerialized = phpserialize.BytesIO()
	for artist in artistList:
#		print ('Artist Name: ' + artist)

		albumList = getAlbumList(artist)
		for album in albumList:
#			print ('Album Name: ' + album)
			artwork = uploadArtwork(artist, album)
			albumArray = []
			albumSerialized = phpserialize.BytesIO()

			if not any(item['item_type'] == 'bundle' and item['artist'] == artist and item['album'] == album for item in checkList):
				albumId = uploadPost('bundle', artist, album, '', artwork)
			else:
				with connection.cursor() as cursor:
					sql = 'SELECT post_id from `upload_info` where item_type = "bundle" and artist = %s and album = %s'
					cursor.execute(sql, (artist, album))
					albumId = cursor.fetchone()['post_id']
				print ('This album already exists - ' + album)

			songList = getSongList(artist, album)
			for song in songList:
#				print ('Song Name: ' + song)
				if not any(item['item_type'] == 'single' and item['artist'] == artist and item['album'] == album and item['song'] == song for item in checkList):
					artwork = uploadArtwork(artist, album)
					songId = uploadPost('single', artist, album, song, artwork)
					albumArray.append(songId)
				else:
					with connection.cursor() as cursor:
						sql = 'SELECT post_id from `upload_info` where item_type = "single" and artist = %s and album = %s and song = %s'
						cursor.execute(sql, (artist, album, song))
						songId = cursor.fetchone()['post_id']
					albumArray.append(songId)
					print ('This song already exists -' + song)

			phpserialize.dump(albumArray, albumSerialized)
			with connection.cursor() as cursor:
				sql1 = 'INSERT INTO `wp9r_postmeta` (`post_id`, `meta_key`, `meta_value`) VALUES (%s, "_edd_product_type", "bundle") ON DUPLICATE KEY UPDATE `meta_value` = "bundle"'
				sql2 = 'INSERT INTO `wp9r_postmeta` (`post_id`, `meta_key`, `meta_value`) VALUES (%s, "_edd_bundled_products", %s) ON DUPLICATE KEY UPDATE `meta_value` = %s'
				cursor.execute(sql1, (albumId))
				cursor.execute(sql2, (albumId, albumSerialized.getvalue(), albumSerialized.getvalue()))
				connection.commit()
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



