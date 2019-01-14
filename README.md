Svitla test task
=====================================

Prerequisites
-------------
- Docker
- docker-compose

Run project
-----------
```
sudo docker-compose up
```


Defining landmarks
---------------------

Landmarks are defined in **landmark.txt** file using the next rule

<Name of any literal words> <X coordinate (int)> <Y coordinate (int)>



Defining instructions
---------------------

Instructions are defined in **instructions.txt** file using the next rules:


First instruction should be starting point:
Start at (X, Y)


If you want to go to Specific be sure that it has correct direction and coordinates route and use next rule using name in quotes:

**Go until you reach landmark "[Landmark Name]"**


If you want to go concrete distance in the concrete direction use next rule :

**Go / Move <distance> blocks**


If you want to keep moving with your direction on concrete distance use:

**Turn West / East / South / North [distance] blocks**


If you want to change the direction turning use :

**Turn right / left**



Example
---------------------

Start at (100, 100)

Go North 20 blocks

Turn right

Go 113 blocks

Turn right

Turn right

Move 13 blocks

Go South 110 blocks

Turn right

go until you reach landmark "Main Square"



