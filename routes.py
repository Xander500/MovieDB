from dbtourprod import dbtour_app
from flask import render_template, request, url_for, redirect
import sqlite3
import redis
import pymongo

@dbtour_app.route("/")
def landingPage():

    clicked = False

    sortBy = 'Media.name'
    
    if 'sortBy' in request.args:
        sortBy = request.args['sortBy']
        clicked = True

    if 'sortWay' in request.args:
        if request.args['sortBy'] == request.args['sortWay']:
            sortBy = sortBy + " " + 'DESC'
            clicked = False
            
    conn = sqlite3.connect("barbieMedia.db")

    #information to be supplied to jinja to make the drop boxes, also takes in information for the drop boxes to alter query
    pickedDirector = ''
    if 'director' in request.args:
        pickedDirector = request.args['director']
    cursor = conn.execute("select DISTINCT director from Media")
    directors = cursor.fetchall()

    pickedYear = ''
    if 'year' in request.args:
        pickedYear = request.args['year']
    cursor = conn.execute("select DISTINCT year from Media")
    years = cursor.fetchall()

    pickedWriter = ''
    if 'writer' in request.args:
        pickedWriter = request.args['writer']
    cursor = conn.execute("select DISTINCT writer from WriterMedia")
    writers = cursor.fetchall()

    #searches for the information needed for table, if the information exists, it alters it query to try to find what was used in the checkbox filters
    cursor = conn.execute("SELECT DISTINCT Media.name,year,director,animationProduction,MIN(WriterMedia.writer) AS HighestWriter FROM Media,WriterMedia,writer WHERE Writer.name=writer AND media=Media.name AND (director=? OR ?='') AND (year=? OR ?='') AND (writer=? OR ?='') GROUP BY Media ORDER BY " + sortBy + " LIMIT 100",(pickedDirector,pickedDirector,pickedYear,pickedYear,pickedWriter,pickedWriter,))
    media = cursor.fetchall()

    # appends all the writers to the table of media by joining it with the information from the writerMedia table
    mediaSpecificWriter = ()
    for row in media:
        cursor = conn.execute("SELECT writer FROM WriterMedia,Media WHERE name=media AND name=? ORDER BY " + sortBy + " LIMIT 100",(row[0],))
        temp = cursor.fetchall()
        mediaSpecificWriter = mediaSpecificWriter + (temp,)
    i = 0
    tempRow = ''
    for row in mediaSpecificWriter:
        for element in row:
            tempRow = tempRow + str(element[0]) + ', '
        media[i] = media[i] + (tempRow,)
        i = i + 1 
        tempRow = ''

    msg = ''
    if 'msg' in request.args:
        msg = request.args['msg']
    #add titles from sqlite to redis
    redisPopulate(media)

    #gets all redis scores in same order, returns a set
    redisScores = ()    
    redisScores = redisGetScores()
    
    #gets all redis titles that are the selected Generation
    redisTitle = 'Nothing Selected'
    redisTitleScore = 'Nothing Selected'
    if 'redisTitle' in request.args:
        redisTitle = request.args['redisTitle']
        redisTitleScore = redisGetScore(redisTitle)

    redisDiscription = redisGetDisc(redisTitle)

    ##MONGO

    mc = getDb()
    db = mc['barbieCharacters']

    if 'redisTitle' in request.args:
        mongoCharacters = list(db.c.find({"media" : redisTitle},{'_id':0,'name':1}))
        if not mongoCharacters:
            mongoCharacters = [{"name" : "No Characters"}]
    else:
        mongoCharacters = [{"name" : "Select a title"}]

    if 'mongoSelectedCharacter' in request.args:
        mongoSelectedCharacter = request.args['mongoSelectedCharacter']
        mongoItems = db.c.find({"media" : redisTitle, "name" : mongoSelectedCharacter},{'_id':0,'name':0,'media':0})
        mongoItems = mongoItems.next()
    else:
        mongoItems = {"Nothing" : "Selected"}    

    print(mongoCharacters)
    print(mongoItems)

    return render_template("landingPage.html",media=media,directors=directors,years=years,writers=writers,msg=msg,clicked=clicked,sortBy=sortBy,redisScores=redisScores,redisDiscription=redisDiscription,redisTitle=redisTitle,redisTitleScore=redisTitleScore,mongoCharacters=mongoCharacters,mongoItems=mongoItems)


@dbtour_app.route("/addMedia")
def addMedia():
    failureMsg = ''
    if 'failed' in request.args:
        failureMsg = "friendly error message."
        
    return render_template("addMedia.html",failureMsg=failureMsg)


@dbtour_app.route("/addMediaHelper")
def addMediaHelper():
    try:
        conn = sqlite3.connect("barbieMedia.db")
        conn.execute("INSERT INTO Media VALUES(?,?,?,?)",(request.args['title'],request.args['year'],request.args['director'],request.args['animationStudio'],))
       
        splitWriters = request.args['writers'].split(',')
        
        for writer in splitWriters:
            conn.execute("INSERT OR IGNORE INTO Writer VALUES(?)",(writer,))
            cursor = conn.execute("SELECT name FROM Media WHERE name=?",(request.args['title'],))
            currentMedia = cursor.fetchall()
            conn.execute("INSERT INTO WriterMedia VALUES(?,?)",(writer,currentMedia[0][0],))   

        conn.commit()

    except sqlite3.IntegrityError as e:
        return redirect(url_for('addMedia',failed=True))   

    return redirect(url_for("landingPage",msg="Successfully added!"))


@dbtour_app.route("/changeMedia")
def changeMedia():
    chosenTitle = request.args['chosenTitle'] 

    conn = sqlite3.connect("barbieMedia.db")
    cursor = conn.execute("SELECT name,year,director,animationProduction FROM Media WHERE name=?",(chosenTitle,))
    mediaRow = cursor.fetchall()

    cursor = conn.execute("SELECT writer From WriterMedia WHERE media=?",(chosenTitle,))
    writersTable = cursor.fetchall()
    writers = ''
    for writerList in writersTable:
        for writer in writerList:
           writers = writers + str(writer) + ',' 
    writers = writers[:-1]
    writerSplit = writers.split(',')       
    return render_template("changeMedia.html",mediaRow=mediaRow,writerSplit=writerSplit,chosenTitle=chosenTitle)


@dbtour_app.route("/changeMediaHelper")
def changeMediaHelper():
    
    #Media
    conn = sqlite3.connect("barbieMedia.db")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("UPDATE Media SET name=?,year=?,director=?,animationProduction=? WHERE name=?",(request.args['title'],request.args['year'],request.args['director'],request.args['animationStudio'],request.args['chosenTitle'],))
    conn.commit()

    #Writer
    i = 0
    for writer in request.args.getlist("curWriter"):

        oldWriter = request.args['writerSplit']

        oldWriter = oldWriter.strip("[]")

        iterable_list = oldWriter.split(",")

        iterable_list = [name.strip().strip("'") for name in iterable_list]


        conn.execute("INSERT OR IGNORE INTO Writer VALUES(?)",(writer,))
        conn.commit()

        if not writer:
            conn.execute("DELETE FROM WriterMedia WHERE media=? AND writer=?",(request.args['title'],iterable_list[i]))
            conn.commit()
            i = i + 1
            continue
       
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("UPDATE WriterMedia SET writer=?,media=? WHERE writer=? AND media=?",(writer,request.args['title'],iterable_list[i],request.args['title'],))
        conn.commit()
        i = i + 1

    #New Writers

    if not request.args.getlist("writers")[0] == "":
        if request.args.getlist("writers"):
            newSplitWriters = request.args.getlist("writers")
            for neWriter in newSplitWriters:
                conn.execute("INSERT OR IGNORE INTO Writer VALUES(?)",(neWriter,))
                conn.execute("INSERT INTO WriterMedia VALUES(?,?)",(neWriter,request.args['title'],))   
      
                conn.commit()

    title = request.args.get('title')
    if title == "":
        conn.execute("DELETE FROM Media WHERE name=?",(request.args['title'],))
        conn.commit()

    return redirect(url_for("landingPage",msg="Successfully changed!")) 


@dbtour_app.route("/changeRedis")
def changeRedis():
    redisDiscription = request.args['redisDiscription']
    redisScore = request.args['redisTitleScore']
    redisTitle = request.args['redisTitle']

    return render_template("changeRedis.html",redisDiscription=redisDiscription,redisScore=redisScore,redisTitle=redisTitle)


@dbtour_app.route("/changeRedisHelper")
def changeRedisHelper():
    redisDiscription = request.args['redisDiscription']
    redisScore = request.args['redisTitleScore']
    redisTitle = request.args['redisTitle']

    redisSetDisc(redisTitle,redisDiscription)
    redisAddScore(redisTitle,redisScore)

    return redirect(url_for('landingPage',redisDiscription=redisDiscription,redisTitleScore=redisScore,redisTitle=redisTitle))


@dbtour_app.route("/changeMongoHelper")
def changeMongoHelper():
    print("1")
    mc = getDb()
    db = mc['barbieCharacters']
    print("1")
    media = request.args['characterMedia']
    name = request.args['characterName']
    print("1")
    tempMedia = list(db.c.find({"media" : media})) 
    tempCharacter = list(db.c.find({"media" : media, "name": name})) 
    print("1")
    if len(tempMedia) < 1:
        db.c.insert_one({"media" : media})

    if len(tempCharacter) < 1:
        db.c.update_one({"media": media}, {"$set": {"name" : name}})
    print("1")
    key = request.args['characterKey']
    value = request.args['characterValue']
    print("1")
    db.c.update_one({"media": media, "name" : name},{"$set": {key : value}})

    return redirect(url_for('landingPage'))
    

def getDb():
    return pymongo.MongoClient("mongodb://localhost:27017")

def redisGetScores():
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    scoreSet = ()
    scoreSet = r.zrevrange("MediaScores",0,-1,withscores=True)
    return scoreSet

def redisGetScore(title):
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    scoreSet = ()
    scoreSet = r.zscore("MediaScores",title)
    return scoreSet


def redisAddScore(title,score):
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    r.zadd("MediaScores",{title : score})
    return 1


def redisGetDisc(key):
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    disc = r.hget("discription",key)
    return disc


def redisSetDisc(key,value):
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    r.hset("discription",key,value)
    return 1
    
def redisPopulate(media):
    r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
    keys = r.zrange("MediaScores",0,-1)

## if value of key is less than 0 or equal to -1 then remove esle dont care



##  for row in media:
##      if row[0] not in keys:
##          redisAddScore(row[0],0)

##  for key in keys:
##      found = False
##      for row in media:
##          if key in row:
##              found = True
##              break

##      if not found:
##r.hdel("discription",key)
##          r.zrem("MediaScores",key)


