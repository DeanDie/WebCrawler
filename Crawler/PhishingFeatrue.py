# -*- coding: utf-8 -*-

"""
use to extract the phishing website feature
"""

import re
import urlparse
import requests
from bs4 import BeautifulSoup
import threading, multiprocessing
from concurrent.futures import ThreadPoolExecutor
from phishingDao import urlDB, urlFeatrueDB, pageFeatrueDB
import chardet

from _socket import timeout

# url验证正则
urlPattern = re.compile(r"")

# 分割url paths正则
splitPattern = re.compile("\W")

# ip验证正则
ipPattern = re.compile(r"(\d{1,3}\.){3}\d{1,3}")

# 结尾非css\js\png\ico,开头是http 正则(look-behind requires fixed-width pattern)
#  = re.compile(r"^[H|h][T|t]{2}[P|p].*?(?<!css|\.js|ico|png)$")

#页面后缀
_PAGE_SUFFIX = ("html", "htm", "php", "shtml", "stm", "shtm", "asp", "jsp", "nsp")

#url链接出现(品牌关键词)、(敏感词)
_URL_SENSITIVE_WORDS = ("webscr", "secure", "account", "login", "update", "signin", "banking", "confirm", "@", "-", "~")

#顶级域名
_TOP_DOMAINS = ("com", "vip", "top", "win", "red", "com", "net", "org", "wang", "gov", "edu", "mil", "co", "biz", "name", "info", "mobi", "pro", "travel", "club", "museum", "int", "aero", "post", "rec", "asia", "au", "ad", "ae", "af", "ag", "ai", "al", "am", "an", "ao", "aa", "ar", "as", "at", "au", "aw", "az", "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "bj", "bm", "bn", "bo", "br", "bs", "bt", "bv", "bw", "by", "bz", "ca", "cc", "cf", "cd", "ch", "ci", "ck", "cl", "cm", "cn", "co", "cq", "cr", "cu", "cv", "cx", "cy", "cz", "de", "dj", "dk", "dm", "do", "dz", "ec", "ee", "eg", "eh", "er", "es", "et", "ev", "fi", "fj", "fk", "fm", "fo", "fr", "ga", "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gp", "gr", "gs", "gt", "gu", "gw", "gy", "hk", "hm", "hn", "hr", "ht", "hu", "id", "ie", "il", "im", "in", "io", "iq", "ir", "is", "it", "jm", "jo", "jp", "je", "ke", "kg", "kh", "ki", "km", "kn", "kp", "kr", "kw", "ky", "kz", "la", "lb", "lc", "li", "lk", "lr", "ls", "lt", "lu", "lv", "ly", "ma", "mc", "md", "me", "mg", "mh", "mk", "ml", "mm", "mn", "mo", "mp", "mq", "mr", "ms", "mt", "mu", "mv", "mw", "mx", "my", "mz", "na", "nc", "ne", "nf", "ng", "ni", "nl", "no", "np", "nr", "nt", "nu", "nz", "om", "qa", "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "pr", "pt", "pw", "py", "re", "rs", "ro", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh", "si", "sj", "sk", "sl", "sm", "sn", "so", "sr", "st", "sv", "su", "sy", "sz", "sx", "tc", "td", "tf", "tg", "th", "tj", "tk", "tl", "tm", "tn", "to", "tr", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "um", "us", "uy", "uz", "va", "vc", "ve", "vg", "vi", "vn", "vu", "wf", "ws", "ye", "yt", "za", "zm", "zw", "arts", "com", "edu", "firm", "gov", "info", "net", "nom", "org", "rec", "store", "web")

pre_suffixPattern = re.compile(r'(?:href|src)="http.*?(?<!css|\.js|ico|png)"', re.I)

def checkURL(url):
	"""
	judge a input string is a url
	:param url: url str
	"""
	return urlPattern.match(url) != None

class UrlFeature(object):
	"""
	The :class:`UrlFeature` object. Use to extract the Url feature.
	"""
	def __init__(self, url, i, table):
		self.scheme = None  #url协议√
		self.domainName = None  #域名, 不含www√
		self.port = -1  #网站端口号√, -1表示没有
		self.path = None  #url之后的路径, 全部为小写√

		self.domainNameLens = 0  #域名长度√
		self.domainNameLevels = 0  #域名级数√
		self.urlLens = 0  #长度√
		self.longTermCount = 0  #url中的长词(15个字符以上单词)个数√
		self.urlPathLevels = 0  #url路径级数√
		self.isHttps = False  #是否https协议√
		self.isIP = False  #域名是否为IP形式√
		self.hasKeyWords = False  #敏感词√
		self.hasPoint = False  #路径中是否含点√
		# self.hasPort = False  #是否含端口√
		self.hasTopLevelDomain = False  #url中是否含有顶级域名√
		self.hasHexadecimal = False  #是否为16进制?
		self.url = url
		self.label = i
		self.setValue()
		self.insertIntoDB(table[i])

	def __repr__(self):
		return '<UrlFeature {}>'.format(self.url)

	def insertIntoDB(self, tableName):
		attributes = [
			self.url, self.scheme, self.domainName, self.port, self.path,
		  	self.domainNameLens, self.domainNameLevels, self.urlLens,
			self.longTermCount, self.urlPathLevels,self.isHttps,
		  	self.isIP, self.hasKeyWords, self.hasPoint,
		  	self.hasTopLevelDomain, self.hasHexadecimal, self.label
	  	]

		urlFeatrueDB.insertOne(attributes)

	def setValue(self):
		# url format is like: ‘scheme://netloc/path;params?query#fragment’
		o = urlparse.urlparse(self.url)

		self.scheme = o.scheme
		self.domainName = (o.netloc if o.netloc[:3] != "www" else o.netloc[4:])
		if o.port != None:
			self.port = o.port
		self.path = (
		"" + o.path
		+ (";" if o.params else "") + o.params
		+ ("?" if o.query else "") + o.query
		+ ("#" if o.fragment else "") + o.fragment
		).lower()

		self.domainNameLens = len(self.domainName)
		self.domainNameLevels = len(self.domainName.split("."))
		self.isIP = (True if ipPattern.match(self.domainName) else False)
		self.urlLens = len(self.url)
		self.longTermCount = len(filter(lambda term: len(term)>=15, splitPattern.split(self.domainName + self.path)))
		self.urlPathLevels = len(filter(lambda x: x != "", self.path.split("/")))
		self.isHttps = (self.scheme == 'https')

		paths = self.path.split(".")
		self.hasPoint = (True if (len(paths) > 2) or (len(paths) == 2 and paths[-1].lower() not in _PAGE_SUFFIX) else False)
		self.hasKeyWords = self._check_URL_SensitiveWords()
		self.hasTopLevelDomain = self._check_URL_Paths_TopDemain()

	def _check_URL_SensitiveWords(self):
		"""
		use to check whether the url has sensitive word.
		"""
		for word in _URL_SENSITIVE_WORDS:
			if self.url.find(word):
				return True

		return False

	def _check_URL_Paths_TopDemain(self):
		"""
		use to check whether the url path has top-level domain.
		"""
		for domain in _TOP_DOMAINS:
			if (domain in self.path):
				return True

		return False


class PageFeature(object):
	"""
	The :class:`PageFeature` object. Use to parse and extract the page feature
	"""

	_COPYRIGHT_KEY = ("&copy;", "©")
	_HEADERS = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Encoding': 'gzip, deflate, sdch',
	'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
	'Cache-Control': 'max-age=0',
	'Connection': 'keep-alive',
	'Cookie': 'CUPID=607763183609f4605b630ef6448180a2',
	'Upgrade-Insecure-Requests': '1',
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
	}

	def __init__(self, url, i, table):
		self.url = url
		self.title = ""  #标题√
		self.metaDesc = ""  #描述√
		self.metaKeywords = ""  #关键字√
		self.copyright = ""  #版权
		self.emptyLinks = 0  #空链接数√, 判断依据 1) href="#"
		self.links = 0  #外部链接数√
		self.content = ""  #网页内容√
		self.redirect = False
		self.label = i
		self._parseHtml()
		self.insertIntoDB(table[i])


	def __repr__(self, arg):
		return "<PageFeature {}>".format(self.url)

	def insertIntoDB(self, tableName):
		attributes = [
			self.url, self.title, self.metaDesc, self.metaKeywords,self.content,
			self.copyright, self.emptyLinks, self.links, self.redirect
		]

		pageFeatrueDB.insertOne(attributes)

	def _parseHtml(self):

		"""
		specific logic to parse html pages
		"""
		try:
			r = requests.get(self.url, headers=self._HEADERS, timeout=10)
		# if (r.status_code is 200):
			# 这里可能会有因为r.encoding设置问题，导致后面解析不正确的情况！！

		except Exception as e:
			r = requests.get(self.url, headers=self._HEADERS, timeout=10)
			if r.status_code != 200:
				print("【Error】: url->[{}], request failed -_-!".format(self.url))
				# if self.label == 0:
				# 	failedUrl.append(self.url)

		if r.status_code == 200:

			# http -> https 重定向
			if urlparse.urlparse(self.url).scheme != urlparse.urlparse(r.url).scheme:
				# self.url = r.url
				self.redirect = True

			html = r.content

			str_dict = chardet.detect(html)
			code_type = str_dict['encoding']
			# print code
			if code_type != 'utf-8' and code_type != 'UTF-8':
				html = html
			else:
				html = html.decode('gbk', 'ignore').encode('utf-8')


			soup = BeautifulSoup(html, "html.parser")
			self.title = soup.title.text if (soup.title) else ""
			#####teset###########
			self.title = self.title.encode('gb2312').decode('utf-8')
			# print self.title

			keywords = soup.find_all("meta", attrs={"name": "keywords"})
			self.metaKeywords = keywords[0]["content"] if keywords else ""
			descript = soup.find_all("meta", attrs={"name": "description"})
			self.metaDesc = descript[0]["content"] if descript else ""

		self.emptyLinks = len(soup.find_all(href="#"))
		self.content = soup.body.text
		self.links = self._countLinks(r.text)

	def _countLinks(self, text):
		"""
		find all Outbound links， filter the links contains that end of css\js\png\ico, or start with .\..\#
		:param soup: is the `BeautifulSoup` object of this url site.
		"""
		link = len(pre_suffixPattern.findall(text))
		return link



def handle():

	pool = ThreadPoolExecutor(max_workers=100)

	def work(url):
		pageFeature = PageFeature(url, i, table)
		print "pageFeature --> ", pageFeature.__dict__
		urlFeature = UrlFeature(url, i, table)
		print "urlFeature --> ", urlFeature.__dict__

	table = ["whitelist", "blacklist"]
	for i in range((len(table))):
		urlTable = list(urlDB.fetchAll(table[i]))
		for url in urlTable:
			"""
			use multi threads to handle this extract feature process
			"""
			pool.submit(work, url[0])


if __name__ == '__main__':
	handle()
