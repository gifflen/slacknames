import time
import random
import boto3
import uuid
import string

import logging
from sets import Set
from PIL import Image, ImageFont, ImageDraw


crontable = []
outputs = []

TEAMS = ['Blue', 'Red']
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

s3 = boto3.resource('s3')

def get_channel_name(data):
    return data['channel']


def get_username(data):
    # TODO translate to actual username
    user_id = data['user']
    return user_id



class SpyMasterCard(object):
    def __init__(self):
        self.first_team = TEAMS[0]
        self.grid = {'1': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                     '2': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                     '3': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                     '4': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                     '5': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''}}

        self._choose_player_orders()
        self._populate_grid()
        print self.grid
        #s3.Bucket('slacknames').upload_file('test', 'test.jpg')

    def _choose_player_orders(self):
        teams = list(TEAMS)
        first_player = random.choice(teams)
        teams.remove(first_player)
        self.first_team = first_player
        self.second_team = teams[0]

    # This is ugly but works.
    def _populate_words(self, word, count):
        if count == 0:
            return
        rows = self.grid.keys()
        columns = self.grid['1'].keys()

        row = random.choice(rows)
        column = random.choice(columns)
        if not self.grid[row][column]:
            self.grid[row][column] = word
            self._populate_words(word, count - 1)
        else:
            self._populate_words(word, count)

    def _fill_bystanders(self):
        for key in self.grid.keys():
            for sub_key in self.grid[key].keys():
                if not self.grid[key][sub_key]:
                    self.grid[key][sub_key] = 'brown'

    def _populate_grid(self):
        # 1 kill word
        # 9 first player
        # 8 second player

        self._populate_words("kill", 1)
        self._populate_words(self.first_team, 9)
        self._populate_words(self.second_team, 8)

    def check_guess(self, row, column):
        return self.grid[row][column]


class Game(object):
    def __init__(self, channel):
        self.players = Set()
        self.blue_spymaster = ''
        self.red_spymaster = ''

        self.blue_team = Set()
        self.red_team = Set()
        self.teams = {'Red': [], 'Blue': []}
        self.scores = {'Red': 0, 'Blue': 0}
        self.clues = {'Red': [], 'Blue': []}
        self.channel = channel
        self.play_area = {'1': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '2': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '3': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '4': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''},
                          '5': {'A': '', 'B': '', 'C': '', 'D': '', 'E': ''}}
        self.started = False
        self.spymaster_card = None
        self.current_team = 'Red'
        self.opposing_team = 'Blue'
        self.remaining_guesses = 0
        self.clue_given = False

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
        if self.started:
            self._message_slack("Game has already started.")
            return

        self.fake_players()
        if len(self.players) >= 4:
            self._init_play_area()
            self._select_teams()
            self._select_spymasters()
            self.spymaster_card = SpyMasterCard()
            self.started = True
            self.current_team = self.spymaster_card.first_team
            self.clue_given = False

            self._message_slack("Game Started")
            self._message_slack(
                "RED TEAM SPYMASTER: {}".format(self.red_spymaster))
            self._message_slack("RED TEAM: {}".format(self.red_team))
            self._message_slack(
                "BLUE TEAM SPYMASTER: {}".format(self.blue_spymaster))
            self._message_slack("BLUE TEAM: {}".format(self.blue_team))

            self.print_game()

            self._message_slack(
                'It is {}\'s turn. Spymaster please submit a !clue'.format(
                    self.current_team))
            self.spymaster()

        else:
            self._message_slack("Not enough players to start")
            print "Not enough players"

    def fake_players(self):
        self.join_game('Bill')
        self.join_game('Bob')
        self.join_game('Jill')

    def _change_teams(self):
        self.remaining_guesses = 0
        self.clue_given = False
        current = self.current_team
        opposing = self.opposing_team
        self.current_team = opposing
        self.opposing_team = current
        self._message_slack("Current team is {}".format(self.current_team))

    def _check_team(self, player):
        # if player in self.current_team
        pass

    def guess(self, guess, player):
        if not self.clue_given:
            self._message_slack("Please wait for your spymaster to give a clue")
            return
        # TODO: check player against current team
        # TODO: check reminaing guesses
        # TODO: check if spymaster

        guess = guess.lower()

        log.debug(guess)

        if guess in ['red', 'blue', 'brown']:
            self._message_slack(
                "{} is not a valid clue. Try again".format(guess))
            return
        for row in self.play_area.keys():
            for column in self.play_area[row].keys():
                if self.play_area[row][column].lower() == guess:
                    self.remaining_guesses -= 1
                    guess_type = self.spymaster_card.check_guess(row, column)
                    self.play_area[row][column] = guess_type
                    logging.debug('Guess type: {}'.format(guess_type))
                    if guess_type == 'kill':
                        # TODO: Determine winner
                        self._message_slack(
                            "You've selected the kill word. GAME OVER")
                        # TODO: implement game over
                        return

                    elif guess_type == 'brown':
                        self._message_slack(
                            "You've selected a bystander. Changing Teams")
                        self._change_teams()
                        self.print_game()
                        return

                    elif guess_type != self.current_team:
                        self.scores[self.opposing_team] += 1
                        self._message_slack(
                            "You've selected a opposing agent. Changing Teams")
                        self._change_teams()
                        self.print_game()
                        return

                    elif guess_type == self.current_team:
                        self._message_slack(
                            "You've selected an agent! Congrats!")
                        self.scores[self.current_team] += 1
                        self._message_slack("{} has {} guesses remaining.".format(self.current_team, self.remaining_guesses))
                        self.print_game()
                        return

                    if self.remaining_guesses == 0:
                        self._message_slack(
                            "No Guesses remaining. Changing Teams")
                        self._change_teams()
                        self.print_game()
                        return

                    self._message_slack(
                        "{} Guesses remaining. Please select another agent or !pass".format(
                            self.remaining_guesses))
                    return
        self._message_slack(
            "\"{}\" is not a valid clue. Try again".format(guess))

    def print_game(self):
        #self._message_slack(str(self.play_area))

        # Define the image sizes
        IMAGE_SIZE = (400,400)
        IMAGE_BG_COLOR = "black"
        IMAGE_TYPE = "RGB"

        # Define the text defaults
        TEXT_FILL = None
        TEXT_FONT = ImageFont.load_default()
        TEXT_ALIGN = 'center' # Doesn't work but documentation says it should...
        TEXT_ANCHOR = None
        TEXT_SPACING = 0

        # Other various grid variables
        GRID_SIZE = 5
        GRID_UNIT = IMAGE_SIZE[0] / GRID_SIZE
        GRID_TEXT_OFFSET = GRID_UNIT * .25
        ALPHABET = ("A", "B", "C", "D", "E")

        # Create an image
        image = Image.new(IMAGE_TYPE, IMAGE_SIZE, IMAGE_BG_COLOR)

        # Create an draw object to use when writing text
        draw = ImageDraw.Draw(image)

        # Iterate over the words and draw the text on the grid
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                x = (GRID_UNIT * (i + 1)) - GRID_UNIT + GRID_TEXT_OFFSET
                y = (GRID_UNIT * (j + 1)) - GRID_UNIT + GRID_TEXT_OFFSET
                text = self.play_area[str(i + 1)][ALPHABET[j]]

                draw.multiline_text((x,y), text, TEXT_FILL, TEXT_FONT, TEXT_ANCHOR,
                                    TEXT_SPACING, TEXT_ALIGN)

        # Done with `draw` object
        del draw

        name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15))
        name = name + '.jpg'
        # Return the image
        image.save(name, formage='JPEG')
        s3.Bucket('slacknames').upload_file(name, name, ExtraArgs={'ACL': 'public-read','ContentType': 'image/jpeg'})
        self._message_slack('https://s3.amazonaws.com/slacknames/{}'.format(name))

        #image.save('{}.jpg'.format(self.channel), formage='JPEG')
        #s3.Bucket('slacknames').upload_file('{}.jpg'.format(self.channel), '{}.jpg'.format(self.channel), ExtraArgs={'ACL': 'public-read','ContentType': 'image/jpeg'})
        #self._message_slack('https://s3.amazonaws.com/slacknames/{}.jpg'.format(self.channel))

    def score(self):
        self._message_slack(str(self.scores))

    def pass_team(self):
        self._message_slack("Changing teams")
        self._change_teams()

    def clue(self, clue, count):
        # todo: check spymaster
        # todo: check turn
        if self.clue_given:
            self._message_slack("Clue has already been submitted this round")
            return

        self.clue_given = True
        self.remaining_guesses = int(count) + 1
        self._message_slack("{} have {} guesses reminaing.".format(self.current_team, self.remaining_guesses))

    def spymaster(self):
        log.debug("Attempting to send spymaster his card")
        #outputs.append(['U0E5XLBRP', str(self.spymaster_card.grid)])

        # Define the image sizes
        IMAGE_SIZE = (400,400)
        IMAGE_BG_COLOR = "black"
        IMAGE_TYPE = "RGB"

        # Define the text defaults
        TEXT_FILL = None
        TEXT_FONT = ImageFont.load_default()
        TEXT_ALIGN = 'center' # Doesn't work but documentation says it should...
        TEXT_ANCHOR = None
        TEXT_SPACING = 0

        # Other various grid variables
        GRID_SIZE = 5
        GRID_UNIT = IMAGE_SIZE[0] / GRID_SIZE
        GRID_TEXT_OFFSET = GRID_UNIT * .25
        ALPHABET = ("A", "B", "C", "D", "E")

        # Create an image
        image = Image.new(IMAGE_TYPE, IMAGE_SIZE, IMAGE_BG_COLOR)

        # Create an draw object to use when writing text
        draw = ImageDraw.Draw(image)

        # Iterate over the words and draw the text on the grid
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                x = (GRID_UNIT * (i + 1)) - GRID_UNIT + GRID_TEXT_OFFSET
                y = (GRID_UNIT * (j + 1)) - GRID_UNIT + GRID_TEXT_OFFSET
                text = self.spymaster_card.grid[str(i + 1)][ALPHABET[j]]

                draw.multiline_text((x,y), text, TEXT_FILL, TEXT_FONT, TEXT_ANCHOR,
                                    TEXT_SPACING, TEXT_ALIGN)

        # Done with `draw` object
        del draw

        # Return the image
        name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15))
        name = name + '.jpg'
        # Return the image
        image.save(name, formage='JPEG')
        s3.Bucket('slacknames').upload_file(name, name, ExtraArgs={'ACL': 'public-read','ContentType': 'image/jpeg'})
        outputs.append(['U0E5XLBRP', 'https://s3.amazonaws.com/slacknames/{}'.format(name)])


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
        outputs.append([data['channel'], "Adding you to the game"])
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

    def guess(self, data, guess):
        log.debug("Processing guess for {}".format(guess))
        game = self.find_game_by_name(get_channel_name(data))
        player = get_username(data)
        game.guess(guess, player)

    def print_game(self, data):
        game = self.find_game_by_name(get_channel_name(data))
        game.print_game()

    def score(self, data):
        game = self.find_game_by_name(get_channel_name(data))
        game.score()

    def pass_team(self, data):
        game = self.find_game_by_name(get_channel_name(data))
        game.pass_team()

    def clue(self, data, clue, count):
        game = self.find_game_by_name(get_channel_name(data))
        game.clue(clue, count)

    def print_spymaster_card(self, data):
        game = self.find_game_by_name(get_channel_name(data))
        if game:
            game.spymaster()


GAMES = Games()


def process_message(data):
    log.debug(data)
    if 'text' in data:
        if data['text'].startswith('!'):
            player_input = data['text'].split(' ')
            command = player_input[0]
            param = ''
            param1 = ''
            if len(player_input) > 1:
                param = player_input[1]
            if len(player_input) > 2:
                param1 = player_input[2]

            log.debug(command)
            log.debug(param)

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

            if command == '!guess':
                GAMES.guess(data, param)

            if command == '!clue':
                log.debug("param: {} param1: {}".format(param, param1))
                GAMES.clue(data, param, param1)

            if command == '!pass':
                GAMES.pass_team(data)

            if command == '!score':
                GAMES.score(data)

            if command == '!print':
                GAMES.print_game(data)

            if command == '!help':
                outputs.append([data['channel'], "!newgame !joingame !startgame !endgame !listplayers !guess !clue !pass !score !print !help"])

            if command == '!spymaster':
                GAMES.print_spymaster_card(data)

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
