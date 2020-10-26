#from pysnmp.hlapi import *
from easysnmp import Session
import csv
import argparse


snmp_max_repetitions=100
olt_list = {}
filter_list=[]

class docsisChannel(object):
	def __init__ (self, ifDescr):
		self.ifDescr=ifDescr
		self.status=0
		self.frequency=0.0
		values=self.ifDescr.split('/')
		self.channelid=values[len(values)-1]
		values=ifDescr.split('/')[0]
		self.frameid=values.split(' ')[1]

	def setFrequency(self,frequency):
		self.frequency=frequency

	def setStatus(self,ifAdminStatus):
		self.status=ifAdminStatus

class docsisChannels(object):
	def __init__(self):
		self.upstream_channel = {}
		self.downstream_channel = {}

	def addUpstreamChannel(self,ifDescr):
		self.upstream_channel[ifDescr] = docsisChannel(ifDescr)

parser = argparse.ArgumentParser(description='enable/disable upstream channels of all DCCAPs from OLT')
parser.add_argument('--ip',dest='ip_address',required=True,help='Hostname or IP Address')
parser.add_argument('--olt',dest='olt_name',required=True,help='Name of the OLT')
parser.add_argument('--olt_file', dest='olt_file_name', default="",
                    help='File with the list of olts in csv format oltname,IP')
parser.add_argument('--type_channel',dest='type_channel',default="u",help="Export upstream (u), downstream(d) or both (ud)")
parser.add_argument('--community',dest='community',default='u2000_ro',help='SNMP read community')
parser.add_argument('--disUpFreq',dest='disUpFreq',default='24.2,19.4,17.8',help='Docsis 3.0 upstream frequencies to disable')
parser.add_argument('--filtercsv',dest='filtercsv',default='',help='List of ipaddress,frameid to avoid doing changes')
#parser.add_argument('--measurement',dest='community',default='u2000_ro',help='SNMP read community')

args = parser.parse_args()

disUpFreq=[]



tmpArray = args.disUpFreq.split(",")
for frequency in tmpArray:
	disUpFreq.append(int(float(frequency)*10000000))

print(disUpFreq)

def setValue(oids,ip_address,community):
	session = Session(hostname=ip_address, community=community, version=2, use_numeric=True)
	output=session.set_multiple(oids)
	print("Setting Value!!!!!")


def pollDocsisChannels(olt_name,ip_address,community):

	session = Session(hostname=ip_address, community=community, version=2, use_numeric=True)

	docsis_channels = docsisChannels()

	upstream_initial_index=1980243960

	finishLoop=False

	while(finishLoop==False):

		oids=[]
		set_oids=[]
		oids.append('IF-MIB::ifDescr.' + str(upstream_initial_index))
		oids.append('IF-MIB::ifAdminStatus.' + str(upstream_initial_index))
		oids.append('.1.3.6.1.2.1.10.127.1.1.2.1.2.' + str(upstream_initial_index)) #Frequency

		docsis_channel_stats = session.get_bulk(oids,non_repeaters=0,max_repetitions=snmp_max_repetitions)
		current_frame=0

		for item in docsis_channel_stats:
			upstream_initial_index=int(item.oid_index)
			if upstream_initial_index >= 2013798401:
				#print("Finishing loop, upstream_initial_index = " + str(upstream_initial_index))
				finishLoop=True
				break
			if item.oid == '.1.3.6.1.2.1.2.2.1.2':#ifDescr
				if "docsCableUpstream" in item.value:
					docsis_channels.upstream_channel[item.oid_index] = docsisChannel(str(item.value))
					docsis_channels.upstream_channel[item.oid_index].ifDescr = str(item.value) #redundancy?
			elif item.oid == '.1.3.6.1.2.1.2.2.1.7':#ifAdminStatus
				if item.oid_index  in docsis_channels.upstream_channel:
					docsis_channels.upstream_channel[item.oid_index].setStatus(str(item.value))
			elif '.1.3.6.1.2.1.10.127.1.1.2.1.2' in item.oid:#Frequency
				#print("upstream_initial_index = " + str(upstream_initial_index))
				if item.oid_index  in docsis_channels.upstream_channel:
					docsis_channels.upstream_channel[item.oid_index].setFrequency(int(item.value))
					current_frame = docsis_channels.upstream_channel[item.oid_index].frameid
					ipAndFrame = ip_address + "," + current_frame
					if ipAndFrame not in  filter_list:
						print("-----Frequency: " + str(int(item.value)))
						if int(item.value) in disUpFreq:
							set_oids.append((item.oid,2))
		
		if len(set_oids)>0:
			setValue(set_oids,ip_address,community)
									
		

	for upstream_channel in docsis_channels.upstream_channel:
		channel_frequency = docsis_channels.upstream_channel[upstream_channel].frequency
		if channel_frequency == 0:
			continue 
		print(olt_name+","+docsis_channels.upstream_channel[upstream_channel].ifDescr + ","+ str(docsis_channels.upstream_channel[upstream_channel].frameid)+ "," + str(docsis_channels.upstream_channel[upstream_channel].channelid) +","+  str(channel_frequency) + "," +  docsis_channels.upstream_channel[upstream_channel].status)


def pollDownstreamDocsisChannels(olt_name,ip_address,community):
  
	session = Session(hostname=ip_address, community=community, version=2, use_numeric=True)

	docsis_channels = docsisChannels()

	downstream_initial_index=2013798400

	finishLoop=False

	while(finishLoop==False):

		oids=[]
		oids.append('IF-MIB::ifDescr.' + str(downstream_initial_index))
		oids.append('IF-MIB::ifAdminStatus.' + str(downstream_initial_index))
		oids.append('.1.3.6.1.2.1.10.127.1.1.1.1.2.' + str(downstream_initial_index)) #Frequency

		docsis_channel_stats = session.get_bulk(oids,non_repeaters=0,max_repetitions=snmp_max_repetitions)


		for item in docsis_channel_stats:
			downstream_initial_index=int(item.oid_index)
			if downstream_initial_index >= 4194312192:
				#print("Finishing loop, upstream_initial_index = " + str(upstream_initial_index))
				finishLoop=True
				break
			if item.oid == '.1.3.6.1.2.1.2.2.1.2':#ifDescr
				if "docsCableDownstream" in item.value:
					docsis_channels.downstream_channel[item.oid_index] = docsisChannel(str(item.value))
					docsis_channels.downstream_channel[item.oid_index].ifDescr = str(item.value) #redundancy?
			elif item.oid == '.1.3.6.1.2.1.2.2.1.7':#ifAdminStatus
				if item.oid_index  in docsis_channels.downstream_channel:
					docsis_channels.downstream_channel[item.oid_index].setStatus(str(item.value))
			elif '.1.3.6.1.2.1.10.127.1.1.1.1.2' in item.oid:#Frequency
				#print("upstream_initial_index = " + str(upstream_initial_index))
				if item.oid_index  in docsis_channels.downstream_channel:
					docsis_channels.downstream_channel[item.oid_index].setFrequency(int(item.value))
									
	for downstream_channel in docsis_channels.downstream_channel:
		channel_frequency = docsis_channels.downstream_channel[downstream_channel].frequency
		if channel_frequency == 0:
			continue 
		print(olt_name+","+docsis_channels.downstream_channel[downstream_channel].ifDescr + "," +str(docsis_channels.downstream_channel[downstream_channel].frameid) +","+str(docsis_channels.downstream_channel[downstream_channel].channelid)+","+str(channel_frequency) + "," +  docsis_channels.downstream_channel[downstream_channel].status)

def polling_olt(olt_name,ip_address,community):
	if(args.type_channel=="u"):
		pollDocsisChannels(olt_name,ip_address,community)
	elif args.type_channel=="d":
		pollDownstreamDocsisChannels(olt_name,ip_address,community)




if args.olt_file_name != "":
	with open(args.olt_file_name) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		for row in csv_reader:
			olt_list[row[0]]=row[1]

if args.filtercsv != "":
	with open(args.filtercsv) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		for row in csv_reader:
			filter_list.append(row)

if len(olt_list)>0:
	for olt_name in olt_list:
		try:
			#print(olt_name)
			polling_olt(args.olt_name,args.ip_address,args.community)
	#		if(args.type_channel=="u"):
	#			pollDocsisChannels(olt_name,olt_list[olt_name],args.community)
	#		elif args.type_channel=="d":
	#			pollDownstreamDocsisChannels(olt_name,olt_list[olt_name],args.community)
		except Exception as e:
			print("olt_name: " + olt_name,e)
			continue
else:
	if(args.olt_name=="" or args.ip_address==""):
		print("Error: OLT name or ip address not defined")
	else:
		polling_olt(args.olt_name,args.ip_address,args.community)

