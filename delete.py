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

wp_url = 'http://www.smochimusic.com/xmlrpc.php'
wp_username = 'yangmike'
wp_password = raw_input("Password: ")
wp = Client(wp_url,wp_username,wp_password)
mediaLibrary = wp.call(media.GetMediaLibrary({}))
connection = pymysql.connect(host='smochimusic.com',
                             user='smochimu_wp153',
                             password='mxbi9gf8n',
                             db='smochimu_wp153',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

def getPostList():
	postList = wp.call(posts.GetPosts({'post_type' : 'download', 'number':999999}))
	return postList

def main():
	postList = getPostList()
	for post in postList:
		success = wp.call(posts.DeletePost(post.id))
		if (success is True):
			with connection.cursor() as cursor:
				sql = 'UPDATE `upload_info` SET published = 0 where post_id = %s'
				cursor.execute(sql, (post.id))
				connection.commit()
		else:
			print ('Couldn\'t delete ' + post.id)
	connection.close()

if __name__ == "__main__":
	main()
