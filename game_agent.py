from PIL import Image
from io import BytesIO
from websocket_server import WebsocketServer
import base64
import json
import multiprocessing
import numpy as np
import threading
import time
import re

class Action:
    UP = 0
    DOWN = 1
    FORWARD = 2


class GameAgent:
    """
    GameAgent class is responsible for passing the actions to the game.
    For this it uses the pyuserinput module.
    A action is performed in the game by emulating a keypress.
    Besides this the GameAgent class is also responsible for retrieving the game status.
    The logic for this is mostly implemented in the ..Handler.. class.
    """
    actions = {Action.UP:'UP', Action.DOWN:'DOWN', Action.FORWARD:'FORWARD'}

    def __init__(self, host, port):
        self.queue = multiprocessing.Queue()
        self.game_client = None
        self.server = WebsocketServer(port, host=host)
        self.server.set_fn_new_client(self.new_client)
        self.server.set_fn_message_received(self.new_message)
        print "GameAgent: Listening..."
        thread = threading.Thread(target = self.server.run_forever)
        thread.daemon = True
        thread.start()

    def new_client(self, client, server):
        print "GameAgent: Game just connected"
        self.game_client = client
        self.server.send_message(self.game_client, "Connection to Game Agent Established");

    def new_message(self, client, server, message):
        print "GameAgent: Incoming data from game"
        data = json.loads(message)
        image, crashed = data['world'], data['crashed']

        # remove data-info at the beginning of the image
        image = re.sub('data:image/png;base64,', '',image)
        # convert image from base64 decoding to np array
        image = np.array(Image.open(BytesIO(base64.b64decode(image))))

        # cast to bool
        crashed = True if crashed in ['True', 'true'] else False

        self.queue.put((image, crashed))

    def startGame(self):
        """
        Starts the game and lets the TRex run for half a second and then returns the initial state.

        :return: the initial state of the game (np.array, reward, crashed).
        """
        # game can not be started as long as the browser is not ready
        while self.game_client is None:
            time.sleep(1)

        self.server.send_message(self.game_client, "START");
        time.sleep(.5)
        return self.get_state()


    def doAction(self, action):
        """
        Performs action and returns the updated status

        :param action:  Must come from the class Action.
                        The only allowed actions are Action.UP, Action.Down and Action.FORWARD.
        :return: return the image of the game after performing the action, the reward (after the action) and
                        whether the TRex crashed or not.
        """
        if not action == Action.FORWARD:
            # noting needs to send when the action is going forward
            self.server.send_message(self.game_client, self.actions[action]);

        time.sleep(1)
        return self.get_state()

    def get_state(self):
        self.server.send_message(self.game_client, "STATE");

        image, crashed = self.queue.get()
        reward = -1 if crashed else 1
        return image, reward, crashed