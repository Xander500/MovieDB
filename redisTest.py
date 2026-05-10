import redis
r = redis.Redis(db=25,password="BenAndJerrys",decode_responses=True)
r.flushdb()

r.zadd("MediaScores",{"Barbie as Rapunzel":85})

r.hset("First","Barbie as the Nutcracker")
r.hset("First","Barbie as Rapunzel")
