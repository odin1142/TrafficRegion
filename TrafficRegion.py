import requests
import json
import math
import gmplot
import polyline
import urllib
import time
from datetime import datetime

#SET THESE VARIABLES

#Insert your Google API key here. The Distance Matrix API has a 2500 element a day limit for the free tier. 
googleAPIKey = INSERTKEYHERE

#Insert Coordinates here
#example: destination = [(38.897685, -77.036487)]
#coordinates are in decimal
destination = [(LATITUDE, LONGITUDE)]

#choices are "best_guess", "pessimistic", or "optimistic"
trafficEstimate = "pessimistic"

#Convert Latitude/Longitude to Miles
latToMiConv = 69.2
longtoMiConv = math.cos(math.radians(destination[0][0]))*69.172

#Set this for timezone
GMTOffset = -5
timeZoneConverter = GMTOffset*60*60

#output .html file name eg "mymap.html"
outputFile = "mymap.html"

#starting radius for search, should be larger than needed but no too large as to burn queries 
distance = 20

#amount that the circle decreases per iteration
radiusStep=1

#number of points on circular that search samples with mesh
meshSize = 100

#max driving time in minutes
maxTime=35
maxTimeSeconds=maxTime*60




def UTCcalc(year,month,day,hour,minute,second):
        #returns epoch time for date
        x = datetime(1970,01,01,00,00,0)
        y = datetime(year,month,day,hour,minute,second)
        return int((y-x).total_seconds())

def parametricPoint(r,a):
        #returns the x,y coordinate of the current circle edge, radius is in miles, angle is radians 
        return r*math.cos(a),r*math.sin(a)

def queryAPI(origins,dest,departTime):
        sendUrl = 'https://maps.googleapis.com/maps/api/distancematrix/json'+'?origins=enc:'+origins+':&destinations=enc:'+dest+':&departure_time='+str(departTime)+"&traffic_model="+trafficEstimate+'&key='+googleAPIKey
        response = requests.post(sendUrl)
        results = json.loads(response.text)
        #check to see if query completed correctly, common error is over query limit
        if(results['status']!="OK"):
                print "Error: "+results['status']
                return -1
        return results

def main():

        #determines the angle in radians for the parametric point calculation
        angle = (math.pi*2)/meshSize

        #initialize validPoint dictionary
        validPoints = {}
        #set destination
        #create array to track points on mesh that are outside of traffic zone
        indexTracker = range(0,meshSize)

        #this needs to be set to a date and time in the future 
        arrivalTime = UTCcalc(2018,02,07,07,30,0) - timeZoneConverter
        departureTime = arrivalTime - maxTimeSeconds 
        queryCount=0

        #continue algorithm until all points in indexTracker are removed, aka all points are within traffic radius
        while len(indexTracker) !=0:
                #create arrays to store current iterations mesh points
                queryCount+=len(indexTracker)
                latitudes,longitudes=[],[]
                for i in indexTracker:
                        #calculate points on circle
                        x,y = parametricPoint(distance,angle*i) #coordinates in miles from origin (set at destination)
                        #convert point to lat/long coord
                        calcX = destination[0][0]+x/latToMiConv
                        calcY = destination[0][1]+y/longtoMiConv
                        latitudes.append(calcX)
                        longitudes.append(calcY)
                        dest = urllib.quote_plus(polyline.encode(destination))
                #encode coordinates with polyline encoding so api request will be under url limit        
                #query API
                tmp=[]
                for i in range(0,int(math.ceil(len(indexTracker)/25.0))):
                        origins = urllib.quote_plus(polyline.encode(zip(latitudes[i*25:25+i*25],longitudes[i*25:25+i*25])))
                        resultsSegment = queryAPI(origins,dest,departureTime)
                        if resultsSegment == -1:
                                return -1
                        tmp.append(resultsSegment['rows'])
                results = [item for sublist in tmp for item in sublist]


                #create check variable to see if any points were within time limit
                indexCheck = 0
                #array of points to remove from indexTracker
                indexRemove = []
                for i in range(0,len(indexTracker)):
                        #check to see if point returned was reachable, occasionally points wont work 
                        if (results[i]['elements'][0]['status']!="OK"):
                                #if point is no good, just skip this step and continue to next index
                                continue
                        #index into results,rows,elements,duration to get the seconds value
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
                #decrement the search radius
                distance -= radiusStep
                #add sleep to prevent reaching query/second limit (I think think its 100 elements a second)
                time.sleep(.5)


        #sort valid points so mapping library makes pretty map
        lat = []
        lon = []
        for key in sorted(validPoints.iterkeys()):
                lat.append(validPoints[key][0])
                lon.append(validPoints[key][1])
        lat.append(validPoints[0][0])
        lon.append(validPoints[0][1])

        # print validPoints
        # print queryCount
        gmap = gmplot.GoogleMapPlotter(destination[0][0],destination[0][1],11)
        gmap.plot(lat,lon,'cornflowerblue',edge_width=3)
        gmap.draw(outputFile)

if __name__ == '__main__':
        main()
