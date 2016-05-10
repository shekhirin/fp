import tornado 
import tornado.web
import tornado.auth
import datetime
from BaseHandler import BaseHandler
import json
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.externals import joblib
import numpy as np
import pandas
import random
from math import exp, sqrt
import forecastio
import datetime
from requests.exceptions import HTTPError
import os
import imghdr

from api.sysfunc import sysfunc


lat, lng = 55.27, 65.20
formats = ('png', 'jpg', 'jpeg', 'gif') 
weather_key = '5c256d08f6b478fdb0d1dded1fcaae44' 
decription = {
	10: 'отжимания',
	11: 'потдягивания',
	54: 'поедание круасанчиков',
	777: 'жокирство', 
	778: 'чтение',
	12 : 'пресс',
	13 : 'приседания'
}


class api(BaseHandler):
	def generate_request_return(self, error=-5454):
		description = { #описание ошибок
			-54 : "?",
			-5454 : 'Undefinded error',
			-10: 'Bad format',
			-504: 'Service error',
			-90: 'Wrong premissions (secure or no data)',
			1:'sucsess',
			-11: 'Bad length', 
			-12: 'Insufficient data',
			-13: 'The number required',
			-14: 'The number must me positive', 
			-15: 'Bad extype',
			-20: 'Bad size',
			-21: 'Bad format',
		}
		try: return({'code':error, 'description':description[error]}) #JSON!
		except BaseException: return({'code':error, 'description':description[-5454]}) #JSON!



	def get(self):
		self.write("<script src='https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js'></script>api ;)")

	@tornado.web.authenticated
	def post(self, z=None):
		self.data = { "exer" : (10,11,54, 777, 6698, 778, 12, 13)} #общедоступные упражнения

			
		request = self.request.uri.split('/')
		try:
		
			if request[2].lower().strip() == 'upd':
					#МЕТОД API: обновление
					jtype = self.get_argument("type").lower()
					if jtype == 'push_excer':
						#отправка данных по выполненному упражнению
						exer_code = int(self.get_argument("exer_code"))
						if int(exer_code) in self.data['exer']:
							try: dpush = int(self.get_argument("data"))
							except ValueError:
								self.write(self.generate_request_return(-13))
								self.finish()
							if dpush <= 0: 
								self.write(self.generate_request_return(-14))
							else:
								self.database['data.{0}'.format(self.get_current_user())].update({'ex': exer_code},\
									{'$inc':{str(datetime.datetime.now().date()): dpush } }, upsert=True)
								self.database['data.{0}'.format(self.get_current_user())]['stat'].update({'ex': exer_code}, \
									{'$inc': {'_all':dpush,'_count':1}}) 
								self.database['data.system'].update({'config':'main'}, {'$addToSet': {'queue': (self.get_current_user(), exer_code) }})
								self.write({'code':1})
								self.finish()
						else: self.write(self.generate_request_return(-15))
					elif jtype == 'takedata':
						#получнеие данных
						exer_code = int(self.get_argument("exer_code"))
						if int(exer_code) in self.data['exer']:
							predval = systemfunctions.predictdata(exer_code, datetime.datetime.now(), self.get_current_user())
							plnday =  self.database['data.{0}'.format(self.get_current_user())]['stat'].find_one(\
								{'ex': exer_code}, {'_count':1})['_count']
							program = round(((plnday)%30+5 + predval)/2)	
							try:
								srv = self.database['data.{0}'.format(self.get_current_user())].find_one({'ex': exer_code},\
									{str(datetime.datetime.now().date()):1})[str(datetime.datetime.now().date())] 	
							except KeyError:
								srv = 0
							
							self.write({'code':1, 'predval':predval, 'srv':srv, 'program':program})
							
					elif jtype == 'plan':
						#МЕТОД API: работа с планом
						exer_code = int(self.get_argument("exer_code"))
						if int(exer_code) in self.data['exer']:
							self.write(systemfunctions.plan(self.get_current_user(), exer_code))
						
					elif jtype == 'file':
						#работа с файлами
						avatar = file1 = self.request.files['avatar'][0]['body']
						ftype = imghdr.what(None, avatar)
						user = self.get_current_user()
						
						if len(avatar) > 540000:
							self.write(self.generate_request_return(-20))
							self.finish()
						elif ftype not in formats:
							self.write(self.generate_request_return(-21))
							self.finish()
						else:
							
							for i in formats: 
								try: os.remove('static/files/users/{0}.{1}'.format(user, i))
								except FileNotFoundError: pass
							fu = open('static/files/users/{0}.{1}'.format(user, ftype), 'wb+')
							
							self.set_data({'id': int( self.get_current_user() )}, 'users', {'imgurl': '{0}.{1}'.format(user, ftype)})
							
							
							fu.write(avatar)
							fu.close()
							
							self.write(self.generate_request_return(1))
					
					else: 
						try: self.write(dpush, (self.generate_request_return()))
						except BaseException: pass
						
			elif request[2].lower().strip() == 'load':
				#МЕТОД API: получение пользовательской информации
				agr = self.get_argument("aim").lower().strip()
				if agr == 'basic':
					user = self.get_current_user()
					self.write(self.get_user_info(user, ['name', 'email', 'wt', 'ht']))
			
			elif request[2].lower().strip() == 'sys':
				#МЕТОД API: работа с системными функциями
				task = self.get_argument("task").lower().strip()
				
				if task == 'check_firstrun':
					exer_code = int(self.get_argument("exer_code").lower().strip())
					if self.database['data.{0}'.format(self.get_current_user())]['stat'].find_one({'ex': exer_code}) is None:
						self.write({'code':0})
					else:
						self.write(self.generate_request_return())
				elif task == 'ex_opened':
					user = self.get_current_user()
					response = {'code':1}
					response['opened_ex'] = self.get_user_info(self.get_current_user(), ['opened_ex'] )['opened_ex']
					self.write(response)
					self.finish()
					
				elif task == 'ex_decription':
					global decription
					self.write({'code':1, 'decription':decription})
					self.finish()
					
					
				elif task == 'repair_firstrun':
					exer_code = int(self.get_argument("exer_code").lower().strip())
					pushdata = [int(i) for i in self.get_argument("data").lower().strip().split(';')]
					if len(pushdata) != 5:
						self.write(self.generate_request_return(-11))
						self.finish()
						return(None)
					sa = 0
					for i in range(1, 6):
						day = datetime.datetime.now() - datetime.timedelta(days=i)
						ndone = pushdata[i-1]
						sa += ndone
						self.database['data.{0}.stat'.format(self.get_current_user())].update({'ex': exer_code}, {'$inc': {'_all':ndone, '_count':1}}, upsert=True)
						self.database['data.{0}'.format(self.get_current_user())].update({'ex': exer_code}, {'$inc':{str(day.date()): ndone } }, upsert=True) 
						
						
					for i in range(1, 6):
						day = datetime.datetime.now() - datetime.timedelta(days=i)
						ndone = pushdata[i-1]
						systemfunctions.fitdata(exer_code, ndone, day, self.get_current_user())
					
					self.database['data.{0}.stat'.format(self.get_current_user())].update({'ex': exer_code}, {'$set': {'before': sa//5}})
					self.write(self.generate_request_return(1))
					
			elif request[2].lower().strip() == 'set':
				#МЕТОД API: установка пользовательской информации
				lake = self.get_argument("lake").lower().strip() #global/exID
				if lake == 'global':
					allowed = ('name', 'email', 'wt', 'ht')
					task = json.loads(self.get_argument("aim").strip())
					for i in task.keys():
						if i not in allowed:
							self.write(self.generate_request_return(-90))
							self.finish()
					self.set_data( {'id': int( self.get_current_user() )}, 'users', task)
					self.write(self.generate_request_return(1))
					
		except ZeroDivisionError as e:
			self.write(self.generate_request_return())


systemfunctions = sysfunc(api.database)