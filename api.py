import tornado 
import tornado.web
import tornado.auth
#tornado - веб-фреймфорк

import datetime
#модуль для работы с датой и временем

from BaseHandler import BaseHandler

import json
#экспорт и импорт данных в формате JSON 

import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.externals import joblib
#методы машинного обучения

import numpy as np
import pandas
#научные вычисления

import random
from math import exp, sqrt

import forecastio
import datetime

from requests.exceptions import HTTPError
import os
import imghdr


#
#	НАСТРОЙКИ КОНФИГУРАЦИИ
#	для вашего удобства вынес в этот файл
#
lat, lng = 55.27, 65.20 #локальная местность - Курган /TODO: спрашивать местоположение у юзера
formats = ('png', 'jpg', 'jpeg', 'gif')  #Допустимые форматы 
weather_key = '5c256d08f6b478fdb0d1dded1fcaae44' #API-ключ для получения данных с сервия forecastio
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
		print(z)
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
							print('***', ftype, len(avatar))
							
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
						
						#print('data.{0}.stat'.format(self.get_current_user()))
						
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
					print('***\n',task)
					for i in task.keys():
						if i not in allowed:
							self.write(self.generate_request_return(-90))
							self.finish()
					self.set_data( {'id': int( self.get_current_user() )}, 'users', task)
					self.write(self.generate_request_return(1))
					
		except ZeroDivisionError as e:
			print(e)
			self.write(self.generate_request_return())

	
	
	

class fn(): 
	def getweather(self, lat, lng, time):
		"""
		Генерация метеоданных
		"""
		global weather_key
		if abs(time - datetime.datetime.now()).total_seconds() // (60*60) <= 24:
			if self.weather_cache is None:
				print('set cache')
				self.weather_cache =  forecastio.load_forecast(weather_key, lat, lng, time=datetime.datetime.now(),\
				 units="us").hourly().data[datetime.datetime.now().hour].d
				self.weather_cache_time = datetime.datetime.now()
				return(self.weather_cache)
			else:
				if abs(time - self.weather_cache_time).total_seconds() // (60*60) <= 24:
					print('use cache')
					return(self.weather_cache)
					
		return(forecastio.load_forecast(weather_key, lat, lng, time=time, units="us").hourly().data[time.now().hour].d)
		
	def fitdata(self, extype, value, date, uid):
		"""
		Обучение (и формирование) модели машинного обучения
		"""
		try:
			os.makedirs('models/'+str(extype))
		except FileExistsError:
			pass
		
		try: 
			model = joblib.load('models/{0}/{1}.pkl'.format(extype, uid))
		except FileNotFoundError:
			model = RandomForestRegressor(n_estimators=54, max_features ='sqrt')
		
		wdata, counted = self.generatedata(extype, date, uid)
		
		wdata.setdefault('cloudCover', 0)
		model.fit(np.array([wdata['cloudCover'], wdata['dewPoint'], wdata['humidity'], wdata['pressure'], wdata['windSpeed'], wdata['temperature'], wdata['windBearing'],  counted[0], counted[1], counted[2], counted[3], counted[4]]).reshape(1,-1), [value]) 
		#print('\tlearn: ...', value)
		joblib.dump(model, 'models/{0}/{1}.pkl'.format(extype, uid)) 
		
	def generatedata(self, extype, date, uid, zeros=False, autocacl=True):
		"""
		Функция генерации данных для обучения и работы с моделью
		"""
		wdata = self.getweather(lat, lng, date) #получение данных погоды
		rk = api.database['data.{0}'.format(uid)].find_one({'ex':int(extype)}, {'_id':0, 'ex':0}) #учёт статистических данных
		zx = sorted(rk.keys())[-5:]
		rk = [rk[i] for i in zx]
			
		counted = []
		for key, wdate in enumerate(zx):
			delta = abs(datetime.datetime.strptime(wdate, "%Y-%m-%d").date() -\
			 datetime.datetime.now().date()).total_seconds() / (60*60*24) #учёт временного интервала
			counted.append(sqrt(rk[key])/2**delta )
		
		return(wdata, counted)
		
	def predictdata(self, extype, date, uid, period=1, utp_coef=1.05):
			"""
			Функция прогноза последующего выполнении на основе машинного обучения
			"""
			model = joblib.load('models/{0}/{1}.pkl'.format(extype, uid)) #открытие существующей модели
			if period <= 1: #period - длительность необходимого прогноза
				wdata, counted = self.generatedata(extype, date, uid)
				return(round(model.predict(np.array([wdata['cloudCover'], wdata['dewPoint'],\
					wdata['humidity'], wdata['pressure'], wdata['windSpeed'], wdata['temperature'],\
					wdata['windBearing'],  counted[0], counted[1], counted[2], counted[3], counted[4]])\
				.reshape(1,-1)) [0] * utp_coef )) #использование модели
			result = []
			wdata, counted_base = self.generatedata(extype, date, uid, autocacl=False)
			 
			for i in range(period):
				counted = [sqrt(val)/2**(len(counted_base) - rs - 1)  for rs, val in enumerate(counted_base)] 
				rpdict = round(model.predict(np.array([wdata['cloudCover'], wdata['dewPoint'], wdata['humidity'],\
					wdata['pressure'], wdata['windSpeed'], wdata['temperature'], wdata['windBearing'],  counted[0],\
					 counted[1], counted[2], counted[3], counted[4]]).reshape(1,-1)) [0] * utp_coef**i) #использование модели
				result.append(rpdict)
				counted_base.append(rpdict)
				
			return(result)
				
	
	def plan(self, uid, extype, pediod=5):
		"""
		Функция генерации истории, базового и физического планов, общей программы
		"""
		plnday =  api.database['data.{0}'.format(uid)]['stat'].find_one({'ex': extype},\
			{'_count':1})['_count'] #учёт статистики
		rk = []
		datess = []
		
		try: future = self.predictdata(extype, datetime.datetime.now(), uid, period=pediod)
		except IndexError: return( api.generate_request_return(None, -12) )
		plan = []

		try:
			idol = api.database['data.{0}'.format(uid)]['stat'].find_one({'ex': extype}, {'before':1})['before']
		except KeyError:
			idol =  round(api.database['data.{0}'.format(uid)]['stat'].find_one({'ex': extype}, {'_all':1})['_all'] \
				/ api.database['data.{0}'.format(uid)]['stat'].find_one({'ex': extype}, {'_count':1})['_count'] , 1)
			api.database['data.{0}'.format(uid)]['stat'].update({'ex': extype}, {'$set':{'before':idol}})
		
		program = []
		for dlt in range(pediod): 
			plan.append(self.calculatefufaultprogram(uid, idol, extype, dlt))
			program.append(int(sqrt((plan[-1] * future[dlt]))))
			
			daytofind = datetime.datetime.now() - datetime.timedelta(days=dlt)
			try:
				n = api.database['data.{0}'.format(uid)].find_one({'ex':extype}, {str(daytofind.date()): 1})\
				[str(daytofind.date())] 
			except KeyError: 
				n = 0
			rk.append(n)
			datess.append(str(daytofind.date()))
	
		return({'old':rk, 'old_date':datess, 'future':future, 'plan':plan, 'program':program})
		
	def get_user_url(self, user):
		"""
		Получение аватара
		"""
		try:
			n = api.database['users'].find_one({'id':user}, {'imgurl':1}) ['imgurl']
		except KeyError:
			return('/files/users/default.png')
			
		return('/files/users/'+str(n))
	
	def __init__(self):
		"""
		Функция инициализации
		"""
		self.weather_cache = None
		self.weather_cache_time = None
		
	
	def calculatefufaultprogram(self, user, now, exer_code, plus):
		"""
		Расчёт базового плана
		"""
		x = plus+api.database['data.{0}'.format(user)]['stat'].find_one({'ex': exer_code}, {'_count':1})['_count']
		strategy = 1 #(0)-Постепенно закрепить, (1)-Быстро преумножить
		goal = now*1.1  #Не может быть меньше, чем сейчас
		
		
		if strategy == 0:
		    if (goal-now)/now > 0.5:
		        #режим больших услилий
		        hard_work_days = 5
		        zoom = '*1,*1.25,*1.3,*1.30,*1.45,*1.2,*1.1,*1.1'.split(',')
		        
		    else: 
		        #режим постепенного закрепления
		        hard_work_days = 4
		        zoom = '*1,+1,*1.1,*1.5,+4,*1.2,*1.4,*1.1'.split(',')
		else:
		    if (goal-now)/now > 0.7:
		        #режим наибольшей временной продуктисности
		        hard_work_days = 3
		        zoom = '*1,*1.4,+1,*1.3,+2,*1.2,+1,*1.1'.split(',')
		    
		    else:
		        #пассивный режим преумножения
		        hard_work_days = 2
		        zoom = '*1,*1.25, +1, +2 ,+3, +1,*0.9,+3'.split(',')
		        
		growpc_coef = 2**strategy*((goal-now)/now )/hard_work_days #>0 жэ если рост
		workday = int(7/hard_work_days)
		influence = []
		for i in range((x+1)//7):
			now = int(eval(str(now)+zoom[-1]))
		
		return(int(eval(str(now)+zoom[(x+1)%7]))) #умножение

systemfunctions = fn()