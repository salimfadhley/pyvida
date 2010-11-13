from __future__ import print_function
import inspect
from new import instancemethod 
import pdb
from datetime import datetime, timedelta
import os
import gc
import sys
import glob
from ctypes import c_int
from random import choice, randint
import logging
import logging.handlers
from itertools import cycle

import pygame
from pygame.locals import *#QUIT, K_ESCAPE

ENABLE_EDITOR = True
ENABLE_PROFILING = True
ENABLE_LOGGING = True

if ENABLE_LOGGING:
    log_level = logging.DEBUG #what level of debugging
else:
    log_level = logging.ERROR

LOG_FILENAME = 'pyvida4.log'
log = logging.getLogger('pyvida4')
log.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=60000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
log.addHandler(handler)

log.debug("\n\n======== STARTING RUN ===========")
if not pygame.font: log.warning('Warning, fonts disabled')
if not pygame.mixer: log.warning('Warning, sound disabled')
log.warning("game.scene.camera not implemented yet")
log.warning("broad try excepts around pygame.image.loads")
log.warning("smart load should load non-idle action as default if there is only one action")


# MOUSE ACTIONS 

MOUSE_GENERAL = 0
MOUSE_USE = 1
MOUSE_LOOK = 2
MOUSE_INTERACT = 3

DEBUG_LOCATION = 4
DEBUG_TEXT = 5
DEBUG_STAND = 6
DEBUG_SOLID = 7
DEBUG_CLICKABLE = 8
DEBUG_ANCHOR = 9
DEBUG_WALK = 10
DEBUG_SCALE = 11

#Animation modes
LOOP = 0
PINGPONG = 1

def use_init_variables(original_class):
    """ Take the value of the args to the init function and assign them to the objects' attributes """
    def __init__(self, *args, **kws):
        inspected = inspect.getargspec(self._init_)
        oargs = inspected.args[1:]
        try:
            defaults = dict(zip(oargs, inspected.defaults))
        except:
            import pdb; pdb.set_trace()
        for i, value in enumerate(oargs):
            if i < len(args): #use the arg values
                arg = args[i]
                if value == "interact" and type(args[i]) == str: 
                    arg = get_function(args[i])
                setattr(self, value, arg)
            else: #use default from original __init__ declaration
                setattr(self, value, defaults[value])
        for key, value in kws.items():
            setattr(self, key, value)
        original_class._init_(self, *args, **kws)

    if type(original_class.__init__) == instancemethod:
      original_class._init_ = original_class.__init__
      original_class.__init__ = __init__
    else:
        log.warning("unable to use_init_variables on %s"%original_class)
    return original_class

def create_event(q):
    return lambda self, *args, **kwargs: self.game.queue_event(q, self, *args, **kwargs)

def use_on_events(name, bases, dic):
    """ create a small method for each "on_<x>" queue function """
    for queue_method in [x for x in dic.keys() if x[:3] == 'on_']:
        qname = queue_method[3:]
        log.debug("class %s has queue function %s available"%(name.lower(), qname))
        dic[qname] = create_event(dic[queue_method])
    return type(name, bases, dic)

#def queue_function(f):
#    """ create a small method for an "on_<x>" queue function """
#    name = f.__name__[3:]
#    log.debug("game itself has registered %s as a queue function"%(name))
#    sys._getframe(1).f_locals[name] = create_event(f)
#    return f

class Polygon(object):
    def __init__(self, vertexarray = []):
        self.vertexarray = vertexarray
    def __get__(self):
        return self.vertexarray
    def __set__(self, v):
        self.vertexarray = v
#    def draw(self): #polygon.draw
#        for i in range(1, len(self.vertexarray)):
#            x1,y1 = self.vertexarray[i-1]
#            x2,y2 = self.vertexarray[i]
#            draw_line(x1,y1,x2,y2)

    def get_point(self, i):
        """ return a point by index """
        return self.vertexarray[i]

    def set_point(self, i, x, y):
        self.vertexarray[i] = (x, y)

    def count(self):
        """ number of points in vertex """
        return len(self.vertexarray)    

    def collide(self, x,y):
        """ Returns True if the point x,y collides with the polygon """
        pointsList = self.vertexarray
        xp = [float(p[0]) for p in pointsList]
        yp = [float(p[1]) for p in pointsList]
        # Initialize loop
        c=False
        i=0
        npol = len(pointsList)
        j=npol-1
        while i < npol:
            if ((((yp[i]<=y) and (y<yp[j])) or 
                ((yp[j]<=y) and(y<yp[i]))) and 
                (x < (xp[j] - xp[i]) * (y - yp[i]) / (yp[j] - yp[i]) + xp[i])):
                c = not c
            j = i
            i += 1
        return c
        
#### pygame util functions ####        

def load_image(fname):
    im = None
    try:
        im = pygame.image.load(fname)
    except:
        log.warning("unable to load image %s"%fname)
    return im
        

##### generic helper functions ####

def slugify(txt):
    """ slugify a piece of text """
    txt = txt.replace(" ", "_")
    return txt.replace("'", "_")

def collide(rect, x,y):
        """ text is point x,y is inside rectangle """
        return not ((x < rect[0])
            or (x > rect[2] + rect[0])
            or (y < rect[1])
            or (y > rect[3] + rect[1]))

def get_point(game, destination):
    """ get a point from a tuple, str or destination """
    if type(destination) == str:
        if destination in game.actors: destination = (game.actors[destination].sx, game.actors[destination].sy)
        elif destination in game.items: destination = (game.items[destination].sx, game.items[destination].sy)
        
    elif type(destination) == object:
        destination = (destination.sx, destination.sy)
    return destination

def relative_position(game, parent, pos):
    """ Take global pos and work out where that is inside parent """
    mx,my=pos[0],pos[1]
    log.warning("relative_position ignores anchor points, scaling and rotation")
    return parent.x-mx, parent.y-my

def get_function(basic):
    script = None
    if hasattr(sys.modules['__main__'], basic):
          script = getattr(sys.modules['__main__'], basic)
    elif hasattr(sys.modules['__main__'], basic.lower()):
          script = getattr(sys.modules['__main__'], basic.lower())
    return script


#### pyvida helper functions ####

def editor_menu(game):
                game.menu_fadeOut()
                game.menu_push() #hide and push old menu to storage
                game.set_menu("e_load", "e_save", "e_add", "e_prev", "e_next")
                game.menu_hide()
                game.menu_fadeIn()



def editor_point(game, menuItem, player):
                if type(menuItem) == str: menuItem = game.items[menuItem]
                points = {"e_location": (game.editing.set_x, game.editing.set_y),
#                        "e_anchor": (game.editing.set_x, game.editing.set_y),
                    }
                if menuItem.name in points:
                    game.editing_point = points[menuItem.name]
                else:
                    game.editing_point = None



#### pyvida classes ####

@use_init_variables
class Game(object):
    __metaclass__ = use_on_events
    _scene = None
    player = None
    actors = {}
    items = {}
    scenes = {}
    
    #always on screen
    menu = [] 
    _menus = [] #a stack of menus 
    modals = []
    
    events = []
    _event = None
    
    voice_volume = 1.0
    effects_volume = 1.0
    music_volume = 1.0
    mute_all = False
    font_speech = None
    
    profiling = False 
    enabled_profiling = False
    editing = None #which actor are we editing
    editing_point = None
    enabled_editor = False
    
    actor_dir = "data/actors"
    item_dir = "data/items"
    menuitem_dir = "data/menu" 
    scene_dir = "data/scenes" 
    interface_dir = "data/interface" 

    quit = False
    screen = None
    existing = False #is there a game in progress (either loaded on saved)
   
    def __init__(self, name="Untitled Game", fullscreen=False):
        log.debug("game object created at %s"%datetime.now())
        self.game = self
        self.mouse_mode = MOUSE_GENERAL
        self.fps = int(1000.0/24)  #12 fps
        
    def __getattr__(self, a):
        if not hasattr(self, a): #possibly set up a queue function
            q = getattr(self, "on_%s"%a, None)
            if q: 
                f = create_event(q)
                setattr(self, a, f)
                return f
        return getattr(self, a)

    def add(self, obj, force_cls=None):
        """ add objects to the game """
        if force_cls:
            if force_cls == ModalItem:
                self.modals.append(obj)
                self.items[obj.name] = obj
            else:
                log.error("%s not implement in game.add"%force_cls)
        else:
            if isinstance(obj, Scene):
                self.scenes[obj.name] = obj
            elif type(obj) in [MenuItem, Collection]: #menu items are stored in items
                self.items[obj.name] = obj
            elif isinstance(obj, ModalItem):
                self.modals.append(obj)
                self.items[obj.name] = obj
            elif isinstance(obj, Item):
                self.items[obj.name] = obj
            elif isinstance(obj, Actor):
                self.actors[obj.name] = obj
            else:
                log.error("%s is an unknown %s type, so failed to add to game"%(obj.name, type(obj)))
        obj.game = self
        return obj
        #self._event_finish()
        
    def on_smart(self, player=None):
        """ cycle through the actors, items and scenes and load the available objects """
        for obj_cls in [Actor, Item, Scene]:
            dname = "%s_dir"%obj_cls.__name__.lower()
            for name in os.listdir(getattr(self, dname)):
                log.debug("game.smart loading %s %s"%(obj_cls.__name__.lower(), name))
                if obj_cls == Actor and name in self.actors:
                    log.warning("game.smart skipping %s, already an actor with this name!"%(name))
                elif obj_cls == Item and name in self.items:
                    log.warning("game.smart skipping %s, already an item with this name!"%(name))
                else:
                    a = obj_cls(name)
                    self.add(a)
                    a.smart(self)
        if type(player) == str: player = self.actors[player]
        if player: self.player = player
        self._event_finish()
                
    def on_set_editing(self, obj):
        if self.editing: #free up old object
            pass
        self.editing = obj
        if self.items["e_location"] not in self.menu:
            mitems = ["e_location", "e_anchor", "e_stand", "e_scale", "e_walkarea", "e_talk"]
            self.set_menu(*mitems)
            self.menu_hide(mitems)
            self.menu_fadeIn()
        self._event_finish()
            
    def toggle_editor(self):
            if self.enabled_editor:  #switch off editor
                self.menu_fadeOut()
                self.menu_pop()
                self.menu_fadeIn()
                self.editing = None
                self.enabled_editor = False
                if hasattr(self, "e_objects"): self.e_objects = None #free add object collection
            else:
                editor_menu(self)
                self.enabled_editor = True
                if self._scene and self._scene.objects: self.set_editing(self._scene.objects.values()[0])

    def _on_mouse_press(self, x, y, button, modifiers): #single button interface
        if len(self.modals) > 0: #modals first
            for i in self.modals:
                if i.collide(x,y):
                    i.trigger_interact()
                    return
            return
        for i in self.menu: #then menu
            if i.collide(x,y):
                if i.actions.has_key('down'): i.action = i.actions['down']
                i.trigger_interact()
                return
        if self.enabled_editor and self._scene:
            if self.editing_point: 
                self.editing_point = None
                return
            for i in self._scene.objects.values():
                if i.collide(x, y):
                    if i == self.editing: #assume want to move
                        editor_point(self, "e_location", self.player)
                    else:
                        self.set_editing(i)
                
        else: #regular game interaction
            pass
        for i in self._scene.objects.values(): #then objects in the scene
            if i is not self.player and i.collide(x,y):
#                if i.actions.has_key('down'): i.action = i.actions['down']
                i.trigger_interact()
                return
        #or finally, try and walk the player there.
        self.player.goto((x,y))



    def _on_mouse_move(self, x, y, button, modifiers): #single button interface
        if self.enabled_editor and self.editing_point:
            self.editing_point[0](x)
            if len(self.editing_point)>1: self.editing_point[1](y)               
        for i in self.menu: #then menu
            if i.collide(x,y):
                if i.actions.has_key('over'): i.action = i.actions['over']
            else:
                if i.action and i.action.name == "over":
                    if i.actions.has_key('idle'): i.action = i.actions['idle']

                
    def _on_key_press(self, key):
        for i in self.menu:
            if key == i.key: i.trigger_interact() #print("bound to menu item")
        if ENABLE_EDITOR and key == K_F1:
            self.toggle_editor()
        elif ENABLE_EDITOR and key == K_F2:
            import pdb; pdb.set_trace()
            

    def handle_pygame_events(self):
        m = pygame.mouse.get_pos()
        btn1, btn2, btn3 = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == QUIT:
                self.quit = True
                return
            elif event.type == MOUSEBUTTONUP:
                self._on_mouse_press(m[0], m[1], btn1, None)
            elif event.type == KEYDOWN:
                self._on_key_press(event.key)
        self._on_mouse_move(m[0], m[1], btn1, None)
#            elif event.key == K_ESCAPE:
 #               self.quit = True
  #              return
        
    def run(self, callback=None):
        pygame.init() 
        self.screen = screen = pygame.display.set_mode((1024, 768))
        if self._scene and self.screen:
           self.screen.blit(self._scene.background(), (0, 0))
        pygame.display.set_caption(self.name)
        
        if ENABLE_EDITOR:
            def editor_load(game, menuItem, player):
                log.debug("editor: load scene not implemented")

            def editor_save(game, menuItem, player):
                log.debug("editor: save scene not implemented")
                
            def _editor_cycle(game, collection, player, v):
                if game._scene and len(game._scene.objects)>0:
                    objects = game._scene.objects.values()
                    if game.editing == None: game.editing = objects[0]
                    i = (objects.index(game.editing) + v)%len(objects)
                    log.debug("editor cycle: switch object %s to %s"%(game.editing, objects[i]))
                    game.set_editing(objects[i])
                else:
                    log.warning("editor cycle: no scene or objects in scene to iterate through")

            def editor_next(game, collection, player):
                return _editor_cycle(game, collection, player, 1)

            def editor_prev(game, collection, player):
                return _editor_cycle(game, collection, player, -1)


            def editor_select_object(game, collection, player):
                """ select an object from the collection and add to the scene """
                m = pygame.mouse.get_pos()
                mx,my = relative_position(game, collection, m)
                obj = collection.get_object(m)
                if obj and game._scene:
                    obj.x, obj.y = 500,400
                    obj._editor_add_to_scene = True #let exported know this is new to this scene
                    game._scene.add(obj)
                    editor_select_object_close(game, collection, player)
                    game.set_editing(obj)

            def editor_add(game, menuItem, player):
                """ set up the collection object """
                if hasattr(self, "e_objects") and self.e_objects:
                    e_objects = self.e_objects
                else: #new object
                    e_objects = self.items["e_objects"]
                e_objects.objects = {}
                for i in game.actors.values():
                    if type(i) not in [Collection, MenuItem]: e_objects.objects[i.name] = i
                for i in game.items.values():
                    if type(i) not in [Collection, MenuItem]: e_objects.objects[i.name] = i
                game.menu_fadeOut()
                game.menu_push() #hide and push old menu to storage
                game.set_menu("e_objects_close", "e_objects")
                game.menu_hide()
                game.menu_fadeIn()
                
            def editor_select_object_close(game, collection, player):
                game.menu_fadeOut()
                game.menu_pop()
                game.menu_fadeIn()
            
            
            self.add(MenuItem("e_load", editor_load, (50, 10), (50,-50), "l").smart(self))
            self.add(MenuItem("e_save", editor_load, (90, 10), (90,-50), "s").smart(self))
            self.add(MenuItem("e_add", editor_add, (130, 10), (130,-50), "a").smart(self))
            self.add(MenuItem("e_prev", editor_prev, (170, 10), (170,-50), "[").smart(self))
            self.add(MenuItem("e_next", editor_next, (210, 10), (210,-50), "]").smart(self))
            self.add(Collection("e_objects", editor_select_object, (300, 100), (300,-600), K_ESCAPE).smart(self))
            self.add(MenuItem("e_objects_close", editor_select_object_close, (800, 600), (800,-100), K_ESCAPE).smart(self))
            for i, v in enumerate(["location", "anchor", "stand", "scale", "walkarea", "talk"]):
                self.add(MenuItem("e_%s"%v, editor_point, (100+i*30, 45), (100+i*30,-50), v[0]).smart(self))
            
            
        
        #pygame.mouse.set_visible(0)        
        if callback: callback(self)
        dt = 12 #time passed
        while self.quit == False:
            pygame.time.delay(self.fps)
            if self._scene:
                blank = [self._scene.objects.values(), self.menu, self.modals]
            else:
                blank = [self.menu, self.modals]

            if self._scene and self.screen:
                for group in blank:
                    for obj in group: obj.clear()

            self.handle_pygame_events()
            self.handle_events()

            if self._scene:
                blank = [self._scene.objects.values(), self.menu, self.modals]
            else:
                blank = [self.menu, self.modals]

            if self._scene and self.screen:
                for group in blank:
                    for obj in group: obj._update(dt)
#                for o in self._scene.actors.values(): o._update(dt)

#                for o in self.modals:
#                    screen.blit(self._scene.background(), (o.x, o.y), (o.x, o.y))
#            pygame.display.update()
            if self._scene and self.screen:
                for group in blank:
                    for obj in group: obj.draw()
            pygame.display.flip()            

    def handle_events(self):
        """ check for outstanding events """
        if len(self.events) == 0: return
        if not self._event: #waiting, so do an immediate process 
            e = self.events.pop(0) #stored as [(function, args))]
            log.debug("Doing event %s"%e[0])

            self._event = e
            e[0](*e[1:]) #call the function with the args        
#            try:
 #              e[0](*e[1:]) #call the function with the args        
  #          except:
   #             import pdb; pdb.set_trace()
    
    def queue_event(self, event, *args):
        self.events.append((event, )+(args))
#        log.debug("events %s"%self.events)
        return args[0]

    def stuff_event(self, event, *args):
        """ stuff an event near the head of the queue """
        self.events.insert(0, (event, )+(args))
        return args[0]


    def _event_finish(self): #Game.on_event_finish
        """ start the next event in the game scripter """
#        log.debug("finished event %s, remaining:"%(self._event, self.events)
        self._event = None
        self.handle_events()
    
        
    def remove(self, obj):
        """ remove from the game so that garbage collection can free it up """
        log.warning("game.remove not implemented yet")
        
        
#    def on_move(self, scene, destination):
#        """ transition to scene, and move player if available """    

    def on_load_state(self, scene, state):
        """ load a state from a file inside a scene directory """
        if type(scene) == str: scene = self.scenes[scene]
        sfname = os.path.join(self.scene_dir, os.path.join(scene.name, state))       
        sfname = "%s.py"%sfname
        variables= {}
        if not os.path.exists(sfname):
            log.error("load state: state not found: %s"%sfname)
        else:
            execfile( sfname, variables)
            variables['load_state'](self, scene)
        self._event_finish()

    def on_save_state(self, scene, state):
        """ save a state inside a scene directory """
        self._event_finish()

    def on_scene(self, scene):
        """ change the current scene """
        if type(scene) == str:
            scene = self.scenes[scene]
        self._scene = scene
        log.debug("changing scene to %s"%scene.name)         
        if self._scene and self.screen:
           self.screen.blit(self._scene.background(), (0, 0))
        self._event_finish()
        
        
    def on_click(self, obj):
        """ helper function to chain mouse clicks """
        obj.trigger_interact()
        self._event_finish()
        


    def on_splash(self, image, callback, duration, immediately=False):
#        """ show a splash screen then pass to callback after duration """
 #       self.
        log.warning("game.splash ignores duration and clicks")
        scene = Scene(image)
        scene.background(image)
        #add scene to game, change over to that scene
        self.add(scene)
        self.scene(scene)
        if self.screen:
           self.screen.blit(scene.background(), (0, 0))
        pygame.display.flip()            
        #create and add a modal to block input
#        modal = Modal(image)
#        modal._clickable_area = [0,0,1024,768]
        if callback: callback(self)
#        def close_splash(self, 
#        modal.interact = 
#        self.add(modal)
        #add timed event for callback
#        self.
        self._event_finish()
        
        
    def on_set_menu(self, *args):
        """ add the items in args to the menu """
        args = list(args)
        args.reverse()
        log.debug("set menu to %s"%list(args))
        for i in args:
            if i in self.items: 
                self.menu.append(self.items[i])
            else:
                log.error("Menu item %s not found in MenuItem collection"%i)
        self._event_finish()        
        
    def on_menu_clear(self):
        log.warning("game.menu_clear should use game.remove")
        #for i in self.menu:
        #    del self.menu[i]
        log.debug("clear menu %s"%[x.name for x in self.menu])
        self.menu = []
        self._menus = []
        self._event_finish()        

    def on_menu_fadeOut(self): 
        """ animate hiding the menu """
        for i in self.menu: self.stuff_event(i.on_goto, (i.hx,i.hy))
        log.debug("fadeOut menu using goto %s"%[x.name for x in self.menu])
        self._event_finish()
        
    def on_menu_hide(self, menu_items = None):
        """ hide the menu (all or partial)"""
        if not menu_items:
            menu_items = self.menu
        for i in menu_items:
            if type(i) == str: i = self.items[i]
            self.stuff_event(i.on_place, (i.hx,i.hy))
        log.debug("hide menu using place %s"%[x.name for x in self.menu])
        self._event_finish()

    def on_menu_show(self):
        """ show the menu """
        for i in self.menu: self.stuff_event(i.on_place, (i.sx,i.sy))
        log.debug("show menu using place %s"%[x.name for x in self.menu])
        self._event_finish()
        
    def on_menu_fadeIn(self): 
        """ animate showing the menu """
        log.debug("fadeIn menu, telling items to goto %s"%[x.name for x in self.menu])
        for i in self.menu: self.stuff_event(i.on_goto, (i.sx,i.sy))
        self._event_finish()
        
    def on_menu_push(self):
        log.debug("push menu %s"%[x.name for x in self.menu])
        if self.menu:
            self._menus.append(self.menu)
            self.menu = []
        self._event_finish()

    def on_menu_pop(self):
        if self._menus: self.menu = self._menus.pop()
        log.debug("pop menu %s"%[x.name for x in self.menu])
        self._event_finish()


@use_init_variables
class Action(object):
    def __init__(self, actor=None, name="unknown action", fname=""): 
        self.images = []
        self.index = 0
        self.count = 0
        self.mode = LOOP
        self.step = 1
        
    @property
    def image(self): #return the current image
        if self.images:
            return self.images[self.index%self.count]
        else:
            img = pygame.Surface((10,10))
            log.debug("action %s has no images"%self.name)
        return img
        
    def update(self, dt):
        self.index += self.step
        if self.mode == PINGPONG and self.index == -1: 
            self.step = 1
            self.index = 0
        if self.mode == PINGPONG and self.index == self.count: 
            self.step = -1
            self.index =self.count-1
            
        
    def load(self): 
        """Load an anim from a montage file"""
        anim = None
        fname = os.path.splitext(self.fname)[0]
        if not os.path.isfile(fname+".montage"):
#            images = pyglet.image.load(fname+".png") #image can't be 9000 wide!
            self.images = [pygame.image.load(fname+".png").convert_alpha()]
#            if anchor_x == -1: 
 #               images.anchor_x = int(images.width/2)
#            elif anchor_x:
#                images.anchor_x = anchor_x
#            if anchor_y == -1: 
#                images.anchor_y = int(images.height * 0.15)
#            elif anchor_y:
#                images.anchor_y = anchor_y
#            self.anchor_x = images.anchor_x
#            self.anchor_y = images.anchor_y
        else:
            with open(fname+".montage", "r") as f:
                num, w, h  = [int(i) for i in f.readlines()]
            master_image = pygame.image.load(fname + ".png").convert_alpha()
            master_width, master_height = master_image.get_size()
            for i in xrange(0, num):
    	        self.images.append(master_image.subsurface((i*w,0,w,h)))
        self.count = len(self.images)
        return self

 


class Actor(object):
    __metaclass__ = use_on_events
    def __init__(self, name=None): 
        self.name = name if name else "Unitled %s"%self.__name__
        self._motion_queue = [] #actor's deltas for moving on the screen in the near-future
        self.action = None
        self.actions = {}
        
        self._alpha = 255
        self._alpha_target = 255
        
        self.font_speech = None    
        self._x,     self._y = 0,0      # place in scene
        self._sx,     self._sy = 0,0    # stand point
        self._ax,     self._ay = 0, 0    # anchor point
        self.speed = 10 #speed at which actor moves per frame
        self.inventory = {}
        self.scale = 1.0
        self.scene = None
        self._walk_area = [0,0,0,0]
        self._solid_area = [0,0,0,0]
        self._clickable_area = [0,0,0,0]
        self._image = None
        self._tx, _ty = 0,0 #target for when moving
        self._rect = None
        self.game = None

    
    def _event_finish(self): 
        return self.game._event_finish()

    def get_x(self): return self._x
    def set_x(self, x): self._x = x
    x = property(get_x, set_x)

    def get_y(self): return self._y 
    def set_y(self, y): self._y = y
    y = property(get_y, set_y)

    def get_ax(self): return self._ax + self.x
    def set_ax(self, ax): self._ax = ax - self.x
    ax = property(get_ax, set_ax)

    def get_ay(self): return self._ay + self.y
    def set_ay(self, ay): self._ay = ay - self.y
    ay = property(get_ay, set_ay)
        
    def smart(self, game):
        """ smart actor load """
        if type(self) in [MenuItem, Collection]:
            d = game.menuitem_dir
        elif isinstance(self, ModalItem):
            d = game.item_dir
        elif isinstance(self, Item):
            d = game.item_dir
        elif isinstance(self, Actor):
            d = game.actor_dir
        for action_fname in glob.glob(os.path.join(d, "%s/*.png"%self.name)): #load actions for this actor
            action_name = os.path.splitext(os.path.basename(action_fname))[0]
            self.actions[action_name] = Action(self, action_name, action_fname).load()
            if action_name == "idle": self.action = self.actions[action_name] #default to idle
        if self.action == None and len(self.actions)>0: self.action = self.actions.values()[0] #or default to first loaded
#        try:
#            self._image = pygame.image.load(os.path.join(d, "%s/idle.png"%self.name)).convert_alpha()
        self._clickable_area = self.action.image.get_rect().move(self.x, self.y)
#        except:
#            log.warning("unable to load idle.png for %s"%self.name)
        log.debug("smart load %s %s clickable %s and actions %s"%(type(self), self.name, self._clickable_area, self.actions.keys()))
        return self
        
    def trigger_interact(self):
        """ find an interact function for this actor and call it """
#        fn = self._get_interact()
 #       if self.interact: fn = self.interact
#        if self.name == "e_objects": import pdb; pdb.set_trace()
        if self.interact:
            self.interact(self.game, self, self.game.player)
        else: #else, search several namespaces or use a default
            basic = "interact_%s"%slugify(self.name)
            script = get_function(basic)
            if script:
                script(self.game, self, self.game.player)
            else:
#                if self.on_interact == self._on_interact: #and type(self) != VidaPortal:
                    #warn if using default vida interact and NOT a portal
                log.warning("no interact script for %s (write an interact_%s)"%(self.name, basic))
                self.on_interact(self.game, self)


    def clear(self):
#        print(self._image.get_rect())
#        self.game.screen.blit(self.game._scene.background(), (self.x, self.y), self._image.get_rect())
        if self._rect:
            self.game.screen.blit(self.game._scene.background(), self._rect, self._rect)
        if self.game.editing == self:
            r = self._crosshair((255,0,0), (self.ax, self.ay))
            self.game.screen.blit(self.game._scene.background(), r, r)
#        if self._image:
 #           r = self._image.get_rect().move(self.x, self.y)    
  #          self.game.screen.blit(self._image, r)
      
    
    def _crosshair(self, colour, pt):
        pygame.draw.line(self.game.screen, colour, (pt[0],pt[1]-5), (pt[0],pt[1]+5))
        pygame.draw.line(self.game.screen, colour, (pt[0]-5,pt[1]), (pt[0]+5,pt[1]))
        return Rect(pt[0]-5, pt[1]-5, 11,11)


    def draw(self):
        img = None
        if self.action: img = self.action.image
        if img:
            img.set_alpha(self._alpha)
            r = img.get_rect().move(self.x, self.y)    
            if self.game.editing == self:
                r2 = r.inflate(-2,-2)
                pygame.draw.rect(self.game.screen, (0,255,0), r2, 2)
                self._crosshair((255,0,0), (self.ax, self.ay))
            self._rect = self.game.screen.blit(img, r)

    def _update(self, dt):
        """ update this actor within the game """
        l = len(self._motion_queue)
        dx = 0
        dy = 0
        if l > 0:
            d = self._motion_queue.pop(0)
            dx, dy = d
            self.x += dx
            self.y += dy
            if l == 1: #if queue empty, get some more queue
                self.on_goto((self._tx, self._ty))
        self._clickable_area = Rect(self.x, self.y, self._clickable_area[2], self._clickable_area[3])
        if self._alpha > self._alpha_target: self._alpha -= 1
        if self._alpha < self._alpha_target: self._alpha += 1
        if self.action: self.action.update(dt)
        if hasattr(self, "update"): #run this actor's personalised update function
            self.update(dt)
        
    def collide(self, x,y):
        return collide(self._clickable_area, x, y)
        
    def on_animation_mode(self, action, mode):
        """ set the animation mode on this action """
        self.actions[action].mode = mode
        self._event_finish()
        

    def on_interact(self, game, actor, player):
        """ default interact smethod """
        if isinstance(self, Item): #very generic
            c = ["It's not very interesting",
            "I'm not sure what you want me to do with that.",
            "I've already tried using that, it just won't fit."]
        else: #probably an Actor object
            c = ["They're not responding to my hails",
            "Perhaps they need a good poking.",
            "They don't want to talk to me."]
        if self.game.player: self.game.player.says(choice(c))
        self._event_finish()


    def on_do(self, action):
        """ start an action """
        self.action = self.actions[action]
        log.debug("actor %s does action %s"%(self.name, action))
        self._event_finish()
            
        
    def on_place(self, destination):
        # """ place an actor at this location instantly """
        pt = get_point(self.game, destination)
        self.x, self.y = pt
        log.debug("actor %s placed at %s"%(self.name, destination))
        self._event_finish()
        
    def on_finish_fade(self):
        print("finish fade %s"%self._alpha)
        if self._alpha == self._alpha_target:
            self._event_finish()
             
    def on_fadeIn(self):
        self._alpha = 0
        self._alpha_target = 255
        self.game.stuff_event(self.finish_fade, self)
        self._event_finish()

    def on_fadeOut(self):
        obj._alpha = 255
        obj._alpha_target = 0
        self.game.stuff_event(self.finish_fade, self)
        self._event_finish()

    def on_relocate(self, scene, destination=None):
        # """ relocate this actor to scene at destination instantly """ 
        if type(scene) == str:
            scene = self.game.scenes[scene]
        if destination:
            pt = get_point(self.game, destination)
            self.x, self.y = pt
#        self.game.scene(scene)
        scene.add(self)
        self._event_finish()
    
    def on_goto(self, destination, block=True, modal=False):
        if type(destination) == str:
            destination = (self.game.actors[destination].sx, self.game.actors[destination].sy)
        elif type(destination) == object:
            destination = (destination.sx, destination.sy)
        x,y = self._tx, self._ty = destination
        d = self.speed
        fuzz = 10
        if x - fuzz < self.x < x + fuzz and y - fuzz < self.y < y + fuzz:
#            self.action = self.actions['idle']
            if type(self) in [MenuItem, Collection]:
                self.x, self.y = self._tx, self._ty
            log.debug("actor %s has arrived at %s"%(self.name, destination))
            self.game._event_finish() #signal to game event queue this event is done
        else: #try to follow the path
            dx = int((x - self.x) / 3)
            dy = int((y - self.y) / 3)
            for i in range(3): self._motion_queue.append((dx+randint(-2,2),dy+randint(-2,2)))


    def on_says(self, text, sfx=-1, block=True, modal=True, font=None):
        """ if sfx == -1, try and guess sound file """
        log.debug("actor %s says %s"%(self.name, text))
        def close_msgbox(game, actor, player):
#            game.clearModal()
            game.modals.remove(game.items["msgbox"])
            game.modals.remove(game.items["txt"])
            game.modals.remove(game.items["ok"])
            self._event_finish()
        msg = self.game.add(ModalItem("msgbox", close_msgbox,(54,-400)).smart(self.game))
        self.game.stuff_event(msg.on_goto, (54,40))
        txt = self.game.add(Text("txt", (100,80), (840,170), text), ModalItem)
        ok = self.game.add(Item("ok").smart(self.game), ModalItem)
        ok.place((900,250))
        self._event_finish()
        
class Item(Actor):
    pass
#    _motion_queue = [] #actor's deltas for moving on the screen in the near-future
#    def __init__(self, name="Untitled Item"): 
        

class Text(Actor):
    def __init__(self, name="Untitled Text", pos=(None, None), dimensions=(None,None), text="no text", colour=(0, 200, 214), size=26):
        Actor.__init__(self, name)
        self.x, self.y = pos
        self.w, self.h = dimensions
#        fname = "data/fonts/domesticManners.ttf"
        fname = "data/fonts/vera.ttf"
        self.font = pygame.font.Font(fname, size)
        self.img = self.font.render(text, True, colour)
   

    def draw(self):
        if self.img:
            r = self.img.get_rect().move(self.x, self.y)    
#            if self.game.editing == self:
#                r2 = r.inflate(-2,-2)
#                pygame.draw.rect(self.game.screen, (0,255,0), r2, 2)
#                self._crosshair((255,0,0), (self.ax, self.ay))
            self._rect = self.game.screen.blit(self.img, r)


class ModalItem(Actor):
    """ blocks interactions with actors, items and menu """
    def __init__(self, name="Untitled Menu Item", interact=None, pos=(None, None)): 
        Actor.__init__(self, name)
        self.x, self.y = pos

    def collide(self, x,y): #modals cover the whole screen?
        return True
  
   
class MenuItem(Actor):
    def __init__(self, name="Untitled Menu Item", interact=None, spos=(None, None), hpos=(None, None), key=None): 
        Actor.__init__(self, name)
        self.interact = interact
        if key: self.key = ord(key) if type(key)==str else key #bind menu item to a keyboard key
        self.sx, self.sy = spos
        self.hx, self.hy = hpos #special hide point for menu items
        self.x, self.y = spos

class Collection(MenuItem):
    """ An actor which contains subactors (eg an inventory or directory listing)"""
    def __init__(self, name="Untitled Collection", interact=None, spos=(None, None), hpos=(None, None), key=None): 
        MenuItem.__init__(self, name, interact, spos, hpos, key)
        self.objects = {}
        self.index = 0
    
    def add(self, *args):
        for a in args:
            if type(a) == str and a in self.game.actors: obj = self.game.actors[a]
            elif type(a) == str and a in self.game.items: obj = self.game.items[a]
            else: obj = a
            self.objects[obj.name] = obj

    def _update(self, dt):
        Actor._update(self, dt)
        for i in self.objects.values():
            if type(i) != Collection:
                i._update(dt)
            else:
                log.warning("Collection %s trying to update collection %s"%(self.name, i.name))


    def get_object(self, pos):
        """ Return the object at this spot on the screen in the collection """
        mx,my = pos
        show = self.objects.values()[self.index:]
        for i in show:
            if hasattr(i, "_cr") and collide(i._cr, mx, my): 
                log.debug("Clicked on %s in collection %s"%(i.name, self.name))
                return i
        log.debug("Clicked on collection %s, but no object at that point"%(self.name))
        return None

    def draw(self):
        Actor.draw(self)
        #TODO use inventory action to render, or else create one
        sx,sy=20,20 #padding
        x,y = sx,sy
        dx,dy=40,40
        w,h = self.action.image.get_width(), self.action.image.get_height()
        show = self.objects.values()[self.index:]
        for i in show:
            if i._image:
                iw, ih = i.action.image.get_width(), i.action.image.get_height()
 #               ratio = float(dx)/iw
#                nw, nh = int(iw*ratio), int(ih*ratio)
                img = pygame.transform.scale(i.action.image, (dx, dy))
                r = img.get_rect().move(x+self.x, y+self.y)
                i._cr = r #temporary collection values
                self.game.screen.blit(img, r)
            x += dx
            if float(x)/(w-sy-dx)>1:
                x = sx
                y += dy
                if float(y)/(h-sy-dy)>1:
                    break

#@use_init_variables    
#class Modal(Actor):
#    def __init__(self, name="Untitled Modal"): pass


class Scene(object):
    __metaclass__ = use_on_events
    def __init__(self, name="Untitled Scene"):
        self.name = name
        self.objects = {}
        self.game = None
        self._background = None
        self.walkarea = None
        self.cx, self.cy = 512,384 #camera pointing at position (center of screen)


    def _event_finish(self): 
        return self.game._event_finish()

    def smart(self, game):
        """ smart scene load """
        sdir = os.path.join(os.getcwd(),os.path.join(game.scene_dir, self.name))
        bname = os.path.join(sdir, "background.png")
        if os.path.isfile(bname):
            self.background(bname)
#        for element in glob.glob(os.path.join(sdir,"*.png")): #add foreground elments
#            x,y = 0,0
#            fname = os.path.basename(element[:-4])
#            if os.path.isfile(bname+fname+".details"): #find a details file for each element
#                with open(bname+fname+".details", "r") as f:
#                    x, y  = [int(i) for i in f.readlines()]
#                a = VidaActor(fname, x=x, y=y).createAction("idle", bname+fname)
#                self.foreground.append(a)
#        if os.path.isfile(bname+"scene.scale"):
#            with open(bname+"scene.scale", "r") as f:
#                actor, factor = f.readline().split("\t")
#                self.scales[actor] = float(factor)
#        if walkarea != None:
#            self.addWalkarea(walkarea)
        return self

    def background(self, fname=None):
        if fname:
            self._background = load_image(fname)
        return self._background

    def remove(self, obj):
        """ remove object from the scene """
        del self.objects[obj.name]
        return self
        
    def on_add(self, obj):
        """ removes obj from current scene it's in, adds to this scene """
        if obj.scene:
            obj.scene.remove(obj)
        self.objects[obj.name] = obj
        obj.scene = self
        log.debug("Add %s to scene %s"%(obj.name, self.name))
        self._event_finish()
        
