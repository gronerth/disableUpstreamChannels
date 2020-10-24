#from pysnmp.hlapi import *
from easysnmp import Session
import argparse


snmp_max_repetitions=100

class docsisChannel(object):
	def __init__ (self, ifDescr):
		self.ifDescr=ifDescr
		self.status=0
		self.frequency=0.0

	def setFrequency(self,frequency):
		self.frequency=frequency

	def setStatus(self,ifAdminStatus):
		self.status=ifAdminStatus

class docsisChannels(object):
	def __init__(self):
		self.upstream_channel = {}

	def addUpstreamChannel(self,ifDescr):
		self.upstream_channel[ifDescr] = docsisChannel(ifDescr)



parser = argparse.ArgumentParser(description='enable/disable upstream channels of all DCCAPs from OLT')
parser.add_argument('--ip',dest='ip_address',required=True,help='Hostname or IP Address')
parser.add_argument('--olt',dest='olt_name',required=True,help='Name of the OLT')
parser.add_argument('--community',dest='community',default='u2000_ro',help='SNMP read community')
#parser.add_argument('--measurement',dest='community',default='u2000_ro',help='SNMP read community')

args = parser.parse_args()

session = Session(hostname=args.ip_address, community=args.community, version=2, use_numeric=True)

docsis_channels = docsisChannels()

upstream_initial_index=1980243960

finishLoop=False

while(finishLoop==False):

	oids=[]
	oids.append('IF-MIB::ifDescr.' + str(upstream_initial_index))
	oids.append('IF-MIB::ifAdminStatus.' + str(upstream_initial_index))
	oids.append('.1.3.6.1.2.1.10.127.1.1.2.1.2.' + str(upstream_initial_index)) #Frequency

	docsis_channel_stats = session.get_bulk(oids,non_repeaters=0,max_repetitions=snmp_max_repetitions)


	for item in docsis_channel_stats:
		upstream_initial_index=item.oid_index
		if item.oid == '.1.3.6.1.2.1.2.2.1.2':#ifDescr
			if "docsCableUpstream" in item.value:
				docsis_channels.upstream_channel[item.oid_index] = docsisChannel(str(item.value))
				docsis_channels.upstream_channel[item.oid_index].ifDescr = str(item.value) #redundancy?
		elif item.oid == '.1.3.6.1.2.1.2.2.1.7':#ifAdminStatus
			if item.oid_index  in docsis_channels.upstream_channel:
				docsis_channels.upstream_channel[item.oid_index].setStatus(str(item.value))
		elif '.1.3.6.1.4.1.2011.6.128.1.1.2.43.1.3.' in item.oid:#Frequency
			if item.oid_index  in docsis_channels.upstream_channel:
				docsis_channels.upstream_channel[item.oid_index].setFrequency(int(item.value))
	
	if upstream_initial_index >= 2013798401:
		print("Finishing loop, upstream_initial_index = " + str(upstream_initial_index))
		finishLoop=True

for upstream_channel in docsis_channels.upstream_channel:
	print(docsis_channels.upstream_channel[upstream_channel].ifDescr + "," +  str(docsis_channels.upstream_channel[upstream_channel].frequency) + "," +  docsis_channels.upstream_channel[upstream_channel].status)

