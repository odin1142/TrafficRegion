import requests
import json
import math
import gmplot
import polyline
import urllib
import time
from datetime import datetime



def UTCcalc(year,month,day,hour,minute,second):
        #returns epoch time for date
        x = datetime(1970,01,01,00,00,0)
        y = datetime(year,month,day,hour,minute,second)
        return int((y-x).total_seconds())

def parametricPoint(r,a):
        #returns the x,y coordinate of the current circle edge, radius is in miles, angle is radians 
        return r*math.cos(a),r*math.sin(a)

def queryAPI(origins, departTime):
        sendUrl = 'https://maps.googleapis.com/maps/api/distancematrix/json'+'?origins=enc:'+origins+':&destinations=enc:'+DestinationPoly+':&departure_time='+str(departTime)+"&traffic_model="+TrafficEstimate+'&key='+GoogleAPIKey
        response = requests.post(sendUrl)
        results = json.loads(response.text)
        #check to see if query completed correctly, common error is over query limit
        if(results['status']=="UNKNOWN_ERROR"):
                return -2
        elif(results['status']!="OK"):
                print sendUrl
                print "Query Error: "+results['status']
                return -1
        return results

def mapPoints(validPoints):
        lat = []
        lon = []
        for key in sorted(validPoints.iterkeys()):
                lat.append(validPoints[key][0])
                lon.append(validPoints[key][1])
        lat.append(validPoints[0][0])
        lon.append(validPoints[0][1])

        # print validPoints
        # print queryCount
        gmap = gmplot.GoogleMapPlotter(Destination[0][0],Destination[0][1],11)
        gmap.plot(lat,lon,'cornflowerblue',edge_width=3)
        gmap.draw(OutputFile)
        return

def pointGenerator(indexTracker,latitudes,longitudes,distance):
        for i in indexTracker:
                x,y = parametricPoint(distance,Angle*i) #coordinates in miles from origin (set at destination)
                latPoint = round(Destination[0][0]+x/LatToMiConv,5)
                longPoint = round(Destination[0][1]+y/LongtoMiConv,5)
                latitudes.append(latPoint)
                longitudes.append(longPoint)
        return latitudes, longitudes

def resultsGenerator(indexTracker,latitudes,longitudes,departureTime):
        tmp=[]
        for i in range(0,int(math.ceil(len(indexTracker)/25.0))):
                origins = urllib.quote_plus(polyline.encode(zip(latitudes[i*25:25+i*25],longitudes[i*25:25+i*25])))
                resultsSegment = queryAPI(origins,departureTime)
                if resultsSegment == -2:
                        resultsSegment = queryAPI(origins,departureTime)
                if resultsSegment < 0:
                        return -1
                tmp.append(resultsSegment['rows'])
        results = [item for sublist in tmp for item in sublist]
        return results

def pointChecker(indexTracker, validPoints, results,departureTime, latitudes, longitudes, arrivalTime):
        indexRemove = []
        indexCheck = 0
        for i in range(0,len(indexTracker)):
                if (results[i]['elements'][0]['status']!="OK"):
                        continue
                try:
                        seconds = results[i]['elements'][0]['duration_in_traffic']['value']
                except:
                        continue
                calcArrival = departureTime + seconds
                #check to see if current point is within the traffic region
                if calcArrival < arrivalTime:
                        #add entry to the valid points dictionary
                        a = indexTracker[i]
                        b = latitudes[i]
                        c = longitudes[i]
                        validPoints[a] = [b,c]
                        #mark that indexRemove needs to be cleaned up
                        indexCheck = 1
                        #add current point to the index remove array
                        indexRemove.append(indexTracker[i])
        #remove point from indexTracker
        if indexCheck == 1:
                for i in indexRemove:
                        indexTracker.remove(i)
        return indexTracker,validPoints
        
#SET THESE VARIABLES
#Insert your Google API key here. The Distance Matrix API has a 2500 element a day limit for the free tier. 
GoogleAPIKey = "INSERT API KEY HERE"
#Insert Coordinates here
# Example: White House, Washington, DC
Destination = [(38.89768, -77.03648)]
#coordinates are in decimal, 5 digits provides roughly 11m of accuracy
DestinationPoly = urllib.quote_plus(polyline.encode(Destination))
#choices are "best_guess", "pessimistic", or "optimistic"
TrafficEstimate = "pessimistic"
#Convert Latitude/Longitude to Miles
LatToMiConv = 69.2
LongtoMiConv = math.cos(math.radians(Destination[0][0]))*69.172
#Set this for timezone
GMTOffset = -5
TimeZoneConverter = GMTOffset*60*60
#output .html file name eg "mymap.html"
OutputFile = "WhiteHouseMap.html"
#starting radius for search, should be larger than needed but no too large as to burn queries 
Distance = 10
#amount that the circle decreases per iteration
RadiusStep=1
#number of points on circular that search samples with mesh
MeshSize = 100
#max driving time in minutes
maxTime=35
maxTimeSeconds=maxTime*60
#determines the angle in radians for the parametric point calculation
Angle = (math.pi*2)/MeshSize

def main():
        distance = Distance
        validPoints = {}
        indexTracker = range(0,MeshSize)

        #this needs to be set to a date and time in the future 
        arrivalTime = UTCcalc(2018,02,8,07,30,0) - TimeZoneConverter
        departureTime = arrivalTime - maxTimeSeconds 
        queryCount=0

        while len(indexTracker) !=0:
                print len(indexTracker)
                queryCount+=len(indexTracker)
                latitudes,longitudes=[],[]
                latitudes,longitudes = pointGenerator(indexTracker,latitudes,longitudes, distance)
                results = resultsGenerator(indexTracker,latitudes,longitudes,departureTime)   
                if results == -1:
                        return -1 
                indexTracker,validPoints = pointChecker(indexTracker,validPoints,results, departureTime, latitudes, longitudes, arrivalTime)
                distance -= RadiusStep

                #add sleep to prevent reaching query/second limit (I think think its 100 elements a second)
                time.sleep(.5)

        mapPoints(validPoints)
        return 0

if __name__ == '__main__':
        main()
