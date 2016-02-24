import time
import random

import logging
from sets import Set

crontable = []
outputs = []

TEAMS = ['Blue', 'Red']
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_channel_name(data):
    return data['channel']


def get_username(data):
    # TODO translate to actual username
    user_id = data['user']
    return user_id


class SpyMasterCard(object):
    def __init__(self):
        self.first_plyaer = TEAMS[0]
        self.grid = {}

        self._choose_first_player()
        self._populate_grid()

    def _choose_first_player(self):
        first_player = random.choice(TEAMS)
        self.first_plyaer = first_player
        return first_player

    def _populate_grid(self):
        pass


class Game(object):
    def __init__(self, channel):
        self.players = Set()
        self.blue_spymaster = ''
        self.red_spymaster = ''
        self.blue_team = Set()
        self.red_team = Set()
        self.channel = channel
        self.play_area = {'1': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '2': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '3': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '4': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '5': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''}}
        self.started = False
        self.spymaster_card = None

    def _message_slack(self, message):
        outputs.append([self.channel, message])

    def _init_play_area(self):
        log.debug('Initing Play area')
        word_bank = list(WORDS)

        for key in self.play_area.keys():
            for sub_key in self.play_area[key].keys():
                word = random.choice(word_bank)
                word_bank.remove(word)
                self.play_area[key][sub_key] = word

        print self.play_area

    def _select_teams(self):
        log.debug('Selecting teams')
        players = list(self.players.copy())
        while len(players) > 0:
            choice = random.choice(players)
            print choice
            players.remove(choice)
            if len(self.blue_team) > len(self.red_team):
                self.red_team.add(choice)
            else:
                self.blue_team.add(choice)
        print "Blue team", self.blue_team
        print "Red Team", self.red_team

    def _select_spymasters(self):
        log.debug('Selecting spymasters')
        log.debug(self.red_team)
        log.debug(self.blue_team)
        self.red_spymaster = random.choice(list(self.red_team.copy()))
        self.blue_spymaster = random.choice(list(self.blue_team.copy()))

    def join_game(self, player):
        self.players.add(player)

    def list_players(self):
        self._message_slack(
            "Players: {0} Blue Team: {1} Red Team: {2}".format(self.players,
                                                               self.blue_team,
                                                               self.red_team))

    def start_game(self):
        self.fake_players()
        if len(self.players) >= 4:
            self._init_play_area()
            self._select_teams()
            self._select_spymasters()
            self.started = True
            self._message_slack("Game Started")
            self._message_slack("RED TEAM SPYMASTER: {}".format(self.red_spymaster))
            self._message_slack("RED TEAM: {}".format(self.red_team))
            self._message_slack("BLUE TEAM SPYMASTER: {}".format(self.blue_spymaster))
            self._message_slack("BLUE TEAM: {}".format(self.blue_team))

        else:
            self._message_slack("Not enough players to start")
            print "Not enough players"

    def fake_players(self):
        self.join_game('Bill')
        self.join_game('Bob')
        self.join_game('Jill')


class Games(object):
    def __init__(self):
        self.games = {}

    def new_game(self, data):
        log.debug("Creating a new game")

        channel = get_channel_name(data)
        current_game = self.find_game_by_name(channel)
        if current_game:
            outputs.append(
                [data['channel'], "A game already exists try !joingame"])
            return
        game = Game(channel)
        self.games[channel] = game
        outputs.append([data['channel'], "A new game has been created"])
        self.join_game(data)

    def find_game_by_name(self, channel_name):
        return self.games.get(channel_name)

    def join_game(self, data):
        log.debug("Joining a game")
        outputs.append([data['channel'], "Joining you the game"])
        game = self.find_game_by_name(get_channel_name(data))
        player = get_username(data)
        game.join_game(player)

    def start_game(self, data):
        log.debug("Starting a game")
        game = self.find_game_by_name(get_channel_name(data))
        if isinstance(game, Game):
            game.start_game()
        else:
            outputs.append([data['channel'], "Unable to start game"])

    def end_game(self, data):
        log.debug('Ending a game')
        outputs.append([data['channel'], "Ending the game"])
        channel = get_channel_name(data)
        self.games.pop(channel)

    def list_players(self, data):
        game = self.find_game_by_name(get_channel_name(data))
        game.list_players()


GAMES = Games()


def process_commands(data):
    log.debug(data)
    if 'text' in data:
        if data['text'].startswith('!'):
            command = str(data['text'].split(' ')[0])

            print command

            if command == '!newgame':
                log.debug('Parsed !newgame')
                GAMES.new_game(data)

            if command == '!joingame':
                GAMES.join_game(data)

            if command == '!startgame':
                GAMES.start_game(data)

            if command == '!endgame':
                GAMES.end_game(data)

            if command == '!listplayers':
                GAMES.list_players(data)


def process_message(data):
    process_commands(data)


WORDS = ['AFRICA',
             'AGENT',
             'AIR',
             'ALIEN',
             'ALPS',
             'AMAZON',
             'AMBULANCE',
             'AMERICA',
             'ANGEL',
             'ANTARCTICA',
             'APPLE',
             'ARM',
             'ATLANTIS',
             'AUSTRALIA',
             'AZTEC',
             'BACK',
             'BALL',
             'BAND',
             'BANK',
             'BAR',
             'BARK',
             'BAT',
             'BATTERY',
             'BEACH',
             'BEAR',
             'BEAT',
             'BED',
             'BEIJING',
             'BELL',
             'BELT',
             'BERLIN',
             'BERMUDA',
             'BERRY',
             'BILL',
             'BLOCK',
             'BOARD',
             'BOLT',
             'BOMB',
             'BOND',
             'BOOM',
             'BOOT',
             'BOTTLE',
             'BOW',
             'BOX',
             'BRIDGE',
             'BRUSH',
             'BUCK',
             'BUFFALO',
             'BUG',
             'BUGLE',
             'BUTTON',
             'CALF',
             'CANADA',
             'CAP',
             'CAPITAL',
             'CAR',
             'CARD',
             'CARROT',
             'CASINO',
             'CAST',
             'CAT',
             'CELL',
             'CENTAUR',
             'CENTER',
             'CHAIR',
             'CHANGE',
             'CHARGE',
             'CHECK',
             'CHEST',
             'CHICK',
             'CHINA',
             'CHOCOLATE',
             'CHURCH',
             'CIRCLE',
             'CLIFF',
             'CLOAK',
             'CLUB',
             'CODE',
             'COLD',
             'COMIC',
             'COMPOUND',
             'CONCERT',
             'CONDUCTOR',
             'CONTRACT',
             'COOK',
             'COPPER',
             'COTTON',
             'COURT',
             'COVER',
             'CRANE',
             'CRASH',
             'CRICKET',
             'CROSS',
             'CROWN',
             'CYCLE',
             'CZECH',
             'DANCE',
             'DATE',
             'DAY',
             'DEATH',
             'DECK',
             'DEGREE',
             'DIAMOND',
             'DICE',
             'DINOSAUR',
             'DISEASE',
             'DOCTOR',
             'DOG',
             'DRAFT',
             'DRAGON',
             'DRESS',
             'DRESS',
             'DRILL',
             'DROP',
             'DUCK',
             'DWARF',
             'EAGLE',
             'EGYPT',
             'EMBASSY',
             'ENGINE',
             'ENGLAND',
             'EUROPE',
             'EYE',
             'FACE',
             'FAIR',
             'FALL',
             'FAN',
             'FENCE',
             'FIELD',
             'FIGHTER',
             'FIGURE',
             'FILE',
             'FILM',
             'FIRE',
             'FISH',
             'FLUTE',
             'FLY',
             'FOOT',
             'FORCE',
             'FOREST',
             'FORK',
             'FRANCE',
             'GAME',
             'GAS',
             'GENIUS',
             'GERMANY',
             'GHOST',
             'GIANT',
             'GLASS',
             'GLOVE',
             'GOLD',
             'GRACE',
             'GRASS',
             'GREECE',
             'GREEN',
             'GROUND',
             'HAM',
             'HAND',
             'HAWK',
             'HEAD',
             'HEART',
             'HELICOPTER',
             'HIMALAYAS',
             'HOLE',
             'HOLLYWOOD',
             'HONEY',
             'HOOD',
             'HOOK',
             'HORN',
             'HORSE',
             'HORSESHOE',
             'HOSPITAL',
             'HOTEL',
             'ICE',
             'ICE CREAM',
             'INDIA',
             'IRON',
             'IVORY',
             'JACK',
             'JAM',
             'JET',
             'JUPITER',
             'KANGAROO',
             'KETCHUP',
             'KEY',
             'KID',
             'KING',
             'KIWI',
             'KNIFE',
             'KNIGHT',
             'LAB',
             'LAP',
             'LASER',
             'LAWYER',
             'LEAD',
             'LEMON',
             'LEPRECHAUN',
             'LIFE',
             'LIGHT',
             'LIMOUSINE',
             'LINE',
             'LINK',
             'LION',
             'LITTER',
             'LOCH NESS',
             'LOCK',
             'LOG',
             'LONDON',
             'LUCK',
             'MAIL',
             'MAMMOTH',
             'MAPLE',
             'MARBLE',
             'MARCH',
             'MASS',
             'MATCH',
             'MERCURY',
             'MEXICO',
             'MICROSCOPE',
             'MILLIONAIRE',
             'MINE',
             'MINT',
             'MISSILE',
             'MODEL',
             'MOLE',
             'MOON',
             'MOSCOW',
             'MOUNT',
             'MOUSE',
             'MOUTH',
             'MUG',
             'NAIL',
             'NEEDLE',
             'NET',
             'NEW YORK',
             'NIGHT',
             'NINJA',
             'NOTE',
             'NOVEL',
             'NURSE',
             'NUT',
             'OCTOPUS',
             'OIL',
             'OLIVE',
             'OLYMPUS',
             'OPERA',
             'ORANGE',
             'ORGAN',
             'PALM',
             'PAN',
             'PANTS',
             'PAPER',
             'PARACHUTE',
             'PARK',
             'PART',
             'PASS',
             'PASTE',
             'PENGUIN',
             'PHOENIX',
             'PIANO',
             'PIE',
             'PILOT',
             'PIN',
             'PIPE',
             'PIRATE',
             'PISTOL',
             'PIT',
             'PITCH',
             'PLANE',
             'PLASTIC',
             'PLATE',
             'PLATYPUS',
             'PLAY',
             'PLOT',
             'POINT',
             'POISON',
             'POLE',
             'POLICE',
             'POOL',
             'PORT',
             'POST',
             'POUND',
             'PRESS',
             'PRINCESS',
             'PUMPKIN',
             'PUPIL',
             'PYRAMID',
             'QUEEN',
             'RABBIT',
             'RACKET',
             'RAY',
             'REVOLUTION',
             'RING',
             'ROBIN',
             'ROBOT',
             'ROCK',
             'ROME',
             'ROOT',
             'ROSE',
             'ROULETTE',
             'ROUND',
             'ROW',
             'RULER',
             'SATELLITE',
             'SATURN',
             'SCALE',
             'SCHOOL',
             'SCIENTIST',
             'SCORPION',
             'SCREEN',
             'SCUBA DIVER',
             'SEAL',
             'SERVER',
             'SHADOW',
             'SHAKESPEARE',
             'SHARK',
             'SHIP',
             'SHOE',
             'SHOP',
             'SHOT',
             'SINK',
             'SKYSCRAPER',
             'SLIP',
             'SLUG',
             'SMUGGLER',
             'SNOW',
             'SNOWMAN',
             'SOCK',
             'SOLDIER',
             'SOUL',
             'SOUND',
             'SPACE',
             'SPELL',
             'SPIDER',
             'SPIKE',
             'SPINE',
             'SPOT',
             'SPRING',
             'SPY',
             'SQUARE',
             'STADIUM',
             'STAFF',
             'STAR',
             'STATE',
             'STICK',
             'STOCK',
             'STRAW',
             'STREAM',
             'STRIKE',
             'STRING',
             'SUB',
             'SUIT',
             'SUPERHERO',
             'SWING',
             'SWITCH',
             'TABLE',
             'TABLET',
             'TAG',
             'TAIL',
             'TAP',
             'TEACHER',
             'TELESCOPE',
             'TEMPLE',
             'THEATER',
             'THIEF',
             'THUMB',
             'TICK',
             'TIE',
             'TIME',
             'TOKYO',
             'TOOTH',
             'TORCH',
             'TOWER',
             'TRACK',
             'TRAIN',
             'TRIANGLE',
             'TRIP',
             'TRUNK',
             'TUBE',
             'TURKEY',
             'UNDERTAKER',
             'UNICORN',
             'VACUUM',
             'VAN',
             'VET',
             'WAKE',
             'WALL',
             'WAR',
             'WASHER',
             'WASHINGTON',
             'WATCH',
             'WATER',
             'WAVE',
             'WEB',
             'WELL',
             'WHALE',
             'WHIP',
             'WIND',
             'WITCH',
             'WORM',
             'YARD',
             ]
