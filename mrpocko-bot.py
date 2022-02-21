
import discord
import cv2
import requests
import json
import os
import time

from bs4 import BeautifulSoup

my_secret = '' # token
client = discord.Client()

def get_quote() -> str:
    """
    Funkcia neprijma ziaden parameter.
    Jej vystupom je hotovy string - nahodny citat
    """
	response = requests.get('https://zenquotes.io/api/random')
	json_data = response.json()

	quote = json_data[0]['q']
	author = json_data[0]['a']
	export_line = f'"{quote}" -{author}'

	return(export_line)

def get_place(msg:str) -> str or list:
    """
    Funkcia vracia ciselny kod oblasti v string formate.

    parameter 'msg': uzivatelom zadane mesto alebo miesto v string formate
    """
	choice = msg.split(':') # from !p:Zarnovica make ['!p', 'Zarnovica']

	places = {} # external file # 4252 places in SR # places.json

	with open('places.json', 'r') as places_file:
		places = json.load(places_file) # {'Abraham': '32299', 'Aleksince': '32376', 'Andovce': '32216', ...}

	try:
		return places[choice[1]] # Abraham -> 32299
	
	except KeyError as e:
		return 'Error'

	except Exception as e:
		error_info = []
		error_info.append(e)
		error_info.append('Unexpected Error')
		return error_info


def get_observatory_weather(place_number) -> str:
    """
    Funkcia vyhlada najaktualnejsiu predpoved pocasia na shmu - model aladin - epsgram 2D

    parameter 'place_number': kod oblasti pre ktoru ma vyhladat najaktualnesi epsgram - vystup funkcie get_place(msg)
    """

	timestamp_id = str(time.time())

	aladin_page = 'http://www.shmu.sk/sk/?page=1&id=meteo_num_egram&nwp_mesto='+str(place_number)
	page = requests.get(aladin_page)
	soup = BeautifulSoup(page.content, 'html.parser')
	images = soup.find_all('img')
	epsgrams = []

	for img in images:
		if 'al-epsgram' in str(img):
			epsgrams.append(img)


	src = epsgrams[-1]['src']
	name_list = src.split('/')
	name = name_list[-1] # last one is name 'abc.png'

	name_temp = name.split('.')

	name = name_temp[0]+timestamp_id+'.'+name_temp[1]

	link_actual_epsgram = 'http://www.shmu.sk' + src

	with open(name, 'wb') as f:
		f.write(requests.get(link_actual_epsgram).content) # save working file

	final_file_name = crop_and_merge(name, timestamp_id)

	return final_file_name

def crop_and_merge(name:str, timestamp_id:str) -> str:
    """
    Funcia vracia nazov finalneho suboru na odoslanie na server

    Funkcia oreze povodny epsgram.
    - 1) vrchna cast sekcie teplota a celkova oblacnost
    - 2) rychlost a narazy vetra
    nasledne ich spoji dokopy do jedneho obrazku
    parameter 'name': nazov pracovneho suboru na orezanie
    parameter 'timestamp_id': tzv špecka - casovy kod v string formate pre rozlisenie jednotlivych dopytov
        ak by bota pouzivalo viacero ludi / serverov naraz, nech sa vzajomne neprepisuju
    """
	file_name = name[:-4]
	file_suffix = name[-4:] # last 4 chars .png, .jpg etc

	image = cv2.imread(name)
	y = 0
	x = 0
	height = 350
	width = 600

	crop = image[y:y+height, x:x+width]

	file_one = file_name+'001'+file_suffix
	cv2.imwrite(file_one, crop)
	#cv2.waitKey(0)

	image = cv2.imread(name)
	y = 625
	x = 0
	height = 145
	width = 600
	crop = image[y:y+height, x:x+width]

	file_two = file_name+'002'+file_suffix
	cv2.imwrite(file_two, crop)
	#cv2.waitKey(0)

	img1 = cv2.imread(file_one)
	img2 = cv2.imread(file_two)
	im_v = cv2.vconcat([img1, img2])
	#vis = np.concatenate((img1, img2), axis=1)
	#cv2.imwrite('out.png', vis)
	final_file_name = 'final_'+timestamp_id+'.png'
	cv2.imwrite(final_file_name, im_v)

	os.remove(file_one)
	os.remove(file_two)
	os.remove(name)

	return final_file_name

@client.event
async def on_ready():
	print('Sme zalogovany ako {0.user}'.format(client))

@client.event
async def on_message(message):
	if message.author == client.user:
		return

	if message.content.startswith('!help'):

        help_msg = '''
        Poznám tieto príkazy:\n
        !help - výpis príkazov\n
        !inspiruj - ponúknem ti citát\n
        !p:Banska Bystrica - poviem ti aké bude počasie
        '''
        await message.channel.send(help_msg)

	if message.content.startswith('!inspiruj'):
		## or better for read
		# quote = get_quote()
		# await message.channel.send(quote)
		await message.channel.send(get_quote())

	if message.content.startswith('!p:'):

		msg = message.content
		place_number = get_place(msg)

		if place_number == 'Error':
			await message.channel.send('Zadal si nesprávny názov miesta.')
			await message.channel.send('Vyber si z týchto možností:', file=discord.File('places.json'))
			
		elif isinstance(place_number, list):
			await message.channel.send('Neočakávaná chyba. Prosím, sprav screenshot a pošli mi ho na mail marcelsuleiman@gmail.com aj s popisom.')
		
		else:
			file = get_observatory_weather(place_number)
			await message.channel.send('Pači sa...', file=discord.File(file))
			os.remove(file)

client.run(my_secret)

