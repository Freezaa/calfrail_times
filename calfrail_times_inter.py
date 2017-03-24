# company: Foerster-Technik
# author: Fabian Riedel
# date: 20.03.2017
# script to extract time(s) it takes calves to start drinking from calfrail
# as well as interruptions of drinking if they are bigger than 10 seconds
# input is a log file from calfrail recorded with OpenLog

#import used libraries
import re
import datetime
import csv
import argparse
import time 
from datetime import timedelta

start_time = time.time()

#strings to match from log, recompile them as regular expression object to use 
start = re.compile("(..\...\... - ..\:..\:..)\:... - rhpscmain\[........\]\: (timer started feedingTime: 480000, feedingTimeLazy: 120000)").match
stop = re.compile("(..\...\... - ..\:..\:..)\:... - rhpscmain\[........\]\: (Saugsensor\: 1)").match
none = re.compile("(..\...\... - ..\:..\:..)\:... - rhpscmain\[........\]\: (Exit\. Sende Futterabruf 0)").match
box = re.compile("(..\...\... - ..\:..\:..)\:... - rhpscmain\[........\]\: Anforderung Futteranspruch \- Anzahl Buchten\: .., aktBucht: (..|.), Seite: (.)").match
int_start = re.compile("(..\...\... - ..\:..\:..)\:... - PP_SCHLAUCHPUMPE.\[........\]\: Unterbrechung\: .* ml").match
int_stop = re.compile("(..\...\... - ..\:..\:..)\:... - PP_SCHLAUCHPUMPE.\[........\]\: Fortsetzen\: .* ml").match
exit_feeding = re.compile("(..\...\... - ..\:..\:..)\:... - rhpscmain\[........\]\: Exit. Sende Futterabruf (.*)").match
exit_stop = re.compile("(..\...\... - ..\:..\:..)\:... - PP_SCHLAUCHPUMPE.\[........\]\:  \(Angehalten\) Unterbrechung:").match
strptime = datetime.datetime.strptime

#parser for arguments from cmdline
parser = argparse.ArgumentParser(description="Log file required as argument!")
parser.add_argument('filename')

#open and setup files that will be used to extract from and parse to
f = open(parser.parse_args().filename, "r")                           
w = open("calfrail_times_out.txt", "w")
c = open("calfrail_times_out.csv", "w", newline="")
d = open("calfrail_times_out_drinking_only.csv", "w", newline="")
e = open("calfrail_drinking_pauses.csv", "w", newline="")
tablewriter = csv.writer(c, delimiter=',')
tablewriter.writerow(['Box number', 'Start', 'Stop', 'Time to start', 'Time to exit'])
table2writer = csv.writer(d, delimiter=',')
table2writer.writerow(['Box number', 'Start', 'Stop', 'Time to start'])
tablepwriter = csv.writer(e, delimiter=',')
tablepwriter.writerow(['Box number', 'Start', 'Stop', 'Pause time'])

#variables used to track times, keep is a helper list to calculate time difference 
keep = []
keepo = []
under_30 = 0
under_60 = 0
under_90 = 0
under_120 = 0
not_drinking = 0
feeding = 0
lines = 0
last_int = 0
time_to_exit = 0
#amount = []

#function to convert times extracted from log to datetime object
def time_conversion(matched_time):
	return strptime(matched_time, '%d.%m.%y - %H:%M:%S')

#main for-loop, checks every line if it matches with predefined lines
#calculates time differences and stores them in output files
for line in f:
	lines += 1
	match_start = start(line)
	match_stop = stop(line)
	match_none = none(line)
	match_box = box(line)
	match_exit = exit_feeding(line)
	start_int = int_start(line)
	stop_int = int_stop(line)
	stop_exit = exit_stop(line)
	
	if match_box is not None:
		feeding_box = match_box.group(2)
		feeding_side = match_box.group(3)
		feeding = 1
	#store start and end time in list
	elif match_start is not None:
		time_start = time_conversion(match_start.group(1))
		if not keep:
			keep.insert(0, time_start)
		else:
			keep[0] = time_start
	elif match_stop is not None:
		time_stop = time_conversion(match_stop.group(1))
		if len(keep) == 1:
			keep.insert(1, time_stop)
	elif match_none is not None:
		#amount.append(0)
		time_none = time_conversion(match_none.group(1))
		if len(keep) == 1:
			keep.insert(1, time_none)
	elif stop_exit is not None:
		last_int = 1
		time_stop_exit = time_conversion(stop_exit.group(1))	
	elif start_int is not None and feeding == 1:
		time_int_start = time_conversion(start_int.group(1))
		if not keepo:
			keepo.insert(0, time_int_start)
		else:
			keepo[0] = time_int_start
	elif stop_int is not None and feeding == 1:
		last_int = 0
		time_int_stop = time_conversion(stop_int.group(1))
		if len(keepo) == 1:
			keepo.insert(1, time_int_stop)
	elif match_exit is not None and feeding == 1:
		if last_int == 1:
			time_match_exit = time_conversion(match_exit.group(1))
			time_to_exit = time_match_exit - time_stop_exit
			w.write("   --> time to end: %s box: %s\n" % (time_to_exit, feeding_box))
		feeding_box = 0	
		feeding_side = 0
		feeding = 0
		#amount.append(match_exit.group(2))
	
	if len(keepo) == 2:
		int_dif = keepo[1] - keepo[0]
		if int_dif.total_seconds() >= 10:	
			#print("box %s --> drinking pause: %s timestamp: %s to %s" % (feeding_box, int_dif, keepo[0], keepo[1]))
			w.write("  --> drinking pause: %s timestamp: %s to %s \n" % (int_dif, keepo[0], keepo[1]))
			tablepwriter.writerow([feeding_box, keepo[0], keepo[1], int_dif])
		keepo.clear()
	
	#when two elements are in the list, calculate time difference and write to output files
	#then clear list for next elements
	if len(keep) == 2:
		dif = keep[1] - keep[0]
		if dif.total_seconds() == 119:
			dif = timedelta(seconds = 120)
		w.write("box %s start %s stop %s - time to start: %s \n" % (feeding_box, keep[0], keep[1], dif))
		tablewriter.writerow([feeding_box, keep[0], keep[1], dif, 0])
		if dif.total_seconds() >= 120:
			not_drinking += 1
		elif dif.total_seconds() < 30:
			under_30 += 1
			table2writer.writerow([feeding_box, keep[0], keep[1], dif])
		elif dif.total_seconds() < 60:
			under_60 += 1
			table2writer.writerow([feeding_box, keep[0], keep[1], dif])
		elif dif.total_seconds() < 90:
			under_90 += 1
			table2writer.writerow([feeding_box, keep[0], keep[1], dif])
		elif dif.total_seconds() < 120:
			under_120 += 1
			table2writer.writerow([feeding_box, keep[0], keep[1], dif])
		#print(feeding_box, dif)
		keep.clear()	

#write summary to .csv files	
table2writer.writerow([])
tablewriter.writerow([])
table2writer.writerow(['Under 30s', 'Under 60s', 'Under 90s', 'Under 120s'])	
table2writer.writerow([under_30, under_60, under_90, under_120])
tablewriter.writerow(['Under 30s', 'Under 60s', 'Under 90s', 'Under 120s', '2 minutes'])	
tablewriter.writerow([under_30, under_60, under_90, under_120, not_drinking])

#print out short statistics to cmdline and txt after script has ran
print("%i periods found - %i under 30s, %i under 60s, %i under 90s, %i under 120s and %i not drinking \n --> exported as %s and %s" % 
		(under_30+under_60+under_90+under_120+not_drinking, under_30, under_60, under_90, under_120, not_drinking, w.name, c.name))		
w.write("\n%i periods found - %i under 30s, %i under 60s, %i under 90s, %i under 120s and %i not drinking \n --> exported as %s and %s" % 
		(under_30+under_60+under_90+under_120+not_drinking, under_30, under_60, under_90, under_120, not_drinking, w.name, c.name))	
#print(amount)
print("lines analyzed: %s runtime: %s seconds" % (lines, round(time.time() - start_time, 2)))