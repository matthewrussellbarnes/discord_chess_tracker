import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
import os.path

from chess_game import ChessGame
from chess_cog import ChessCog
class ChessBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix='/', intents=intents)
        self.channel_data = {}  # Will store both current and past games
        self.save_file = 'chess_games.json'
        self.load_games()
        
    def load_games(self):
        """Load saved games from file"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    saved_data = json.load(f)
                    for channel_id, channel_info in saved_data.items():
                        channel_id = int(channel_id)
                        self.channel_data[channel_id] = {
                            'current_game': None,
                            'past_games': []
                        }
                        
                        # Load past games
                        for game_data in channel_info.get('past_games', []):
                            self.channel_data[channel_id]['past_games'].append(
                                ChessGame.from_dict(game_data, self)
                            )
                            
                        # Load current game if it exists
                        if 'current_game' in channel_info:
                            self.channel_data[channel_id]['current_game'] = \
                                ChessGame.from_dict(channel_info['current_game'], self)
            except Exception as e:
                print(f"Error loading games: {e}")
    
    def save_games(self):
        """Save all games to file"""
        try:
            saved_data = {}
            for channel_id, data in self.channel_data.items():
                saved_data[str(channel_id)] = {
                    'current_game': data['current_game'].to_dict() if data['current_game'] else None,
                    'past_games': [game.to_dict() for game in data['past_games']]
                }
            with open(self.save_file, 'w') as f:
                json.dump(saved_data, f)
        except Exception as e:
            print(f"Error saving games: {e}")
    
    def get_current_game(self, channel_id):
        """Helper to get current game for a channel"""
        return self.channel_data.get(channel_id, {}).get('current_game')
    
    async def setup_hook(self):
        await self.add_cog(ChessCog(self))


if __name__ == "__main__":
    load_dotenv()
    bot = ChessBot()
    
    import atexit
    atexit.register(bot.save_games)
    
    bot.run(os.getenv('DISCORD_TOKEN'))