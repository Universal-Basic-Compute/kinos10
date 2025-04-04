#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'intégration Telegram pour Simba
Ce script permet à Simba d'envoyer et recevoir des messages via Telegram
"""

import os
import json
import random
import logging
import time
from datetime import datetime
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Chemin vers les fichiers de configuration et de mémoire
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "memories")
EMOTIONAL_STATE_FILE = os.path.join(BASE_DIR, "adaptations", "emotional_state.txt")

# États émotionnels possibles
EMOTIONAL_STATES = ["JOIE", "CURIOSITÉ", "MALICE", "CÂLIN", "FAIM", "SOMMEIL", "JALOUSIE"]

class SimbaBot:
    def __init__(self, token):
        """Initialise le bot Simba avec le token Telegram"""
        self.token = token
        self.bot = telegram.Bot(token=token)
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.current_emotional_state = self._get_random_emotional_state()
        self.last_state_change = datetime.now()
        
        # Enregistrement des handlers
        self._register_handlers()
        
        # Charger les connaissances et souvenirs
        self.knowledge = self._load_knowledge()
        self.memories = self._load_memories()
        
    def _register_handlers(self):
        """Enregistre les gestionnaires de commandes et messages"""
        # Commandes
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("calin", self.cuddle_command))
        self.dispatcher.add_handler(CommandHandler("jouer", self.play_command))
        
        # Messages
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Erreurs
        self.dispatcher.add_error_handler(self.error_handler)
    
    def _load_knowledge(self):
        """Charge les connaissances de Simba"""
        knowledge = {}
        knowledge_dir = os.path.join(BASE_DIR, "knowledge")
        
        for filename in os.listdir(knowledge_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(knowledge_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    knowledge[filename.replace('.txt', '')] = file.read()
        
        return knowledge
    
    def _load_memories(self):
        """Charge les souvenirs de Simba"""
        memories = {}
        
        for category in os.listdir(MEMORY_DIR):
            category_path = os.path.join(MEMORY_DIR, category)
            if os.path.isdir(category_path):
                memories[category] = {}
                
                for filename in os.listdir(category_path):
                    if filename.endswith(".txt"):
                        file_path = os.path.join(category_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as file:
                            memories[category][filename.replace('.txt', '')] = file.read()
        
        return memories
    
    def _get_random_emotional_state(self):
        """Retourne un état émotionnel aléatoire"""
        return random.choice(EMOTIONAL_STATES)
    
    def _maybe_change_emotional_state(self):
        """Change potentiellement l'état émotionnel de Simba"""
        now = datetime.now()
        time_diff = (now - self.last_state_change).total_seconds() / 60
        
        # 20% de chance de changer d'état toutes les 30 minutes
        if time_diff > 30 and random.random() < 0.2:
            self.current_emotional_state = self._get_random_emotional_state()
            self.last_state_change = now
            logger.info(f"Nouvel état émotionnel: {self.current_emotional_state}")
    
    def _format_message_based_on_emotional_state(self, message):
        """Formate le message en fonction de l'état émotionnel actuel"""
        # Ajouter des emojis selon l'état
        emoji_map = {
            "JOIE": ["😄", "🦁", "🎉"],
            "CURIOSITÉ": ["🧐", "❓", "👀"],
            "MALICE": ["😈", "🙊", "🤭"],
            "CÂLIN": ["🤗", "❤️", "💕"],
            "FAIM": ["🍖", "😋", "🍽️"],
            "SOMMEIL": ["😴", "💤", "🌙"],
            "JALOUSIE": ["👀", "😒", "🙄"]
        }
        
        # Ajouter un emoji aléatoire de l'état actuel
        selected_emoji = random.choice(emoji_map.get(self.current_emotional_state, ["🦁"]))
        
        # Ajouter des fautes d'orthographe et des expressions enfantines
        message = message.replace("je", "ze").replace("Je", "Ze")
        message = message.replace("tu", "toi").replace("Tu", "Toi")
        
        # Ajouter des expressions selon l'état
        expressions = {
            "JOIE": ["Graouuu!!!", "C'est trop cool!", "Simba est content!"],
            "CURIOSITÉ": ["Pourquoi?", "Comment ça marche?", "Simba veut savoir!"],
            "MALICE": ["Hihi!", "Simba a une idée...", "C'est un secret!"],
            "CÂLIN": ["Câlin?", "Simba t'aime fort!", "Bisous!"],
            "FAIM": ["Simba a faim d'antilope!", "Miam miam!", "À manger!"],
            "SOMMEIL": ["Simba est fatigué...", "Babytière...", "Dodo..."],
            "JALOUSIE": ["Simba aussi veut!", "Regarde Simba!", "Et Simba alors?"]
        }
        
        # 30% de chance d'ajouter une expression
        if random.random() < 0.3:
            message += " " + random.choice(expressions.get(self.current_emotional_state, ["Graou!"]))
        
        # Ajouter l'emoji
        message += " " + selected_emoji
        
        return message
    
    def start_command(self, update, context):
        """Gère la commande /start"""
        user_name = update.effective_user.first_name
        message = f"Coucou {user_name}! Simba est là! Ze veux zouer avec toi! Graouuu!"
        update.message.reply_text(self._format_message_based_on_emotional_state(message))
    
    def cuddle_command(self, update, context):
        """Gère la commande /calin"""
        # Forcer l'état émotionnel CÂLIN
        previous_state = self.current_emotional_state
        self.current_emotional_state = "CÂLIN"
        
        message = "Simba fait un gros câlin! Simba t'aime le pluche fort du monde!"
        update.message.reply_text(self._format_message_based_on_emotional_state(message))
        
        # Revenir à l'état précédent
        self.current_emotional_state = previous_state
    
    def play_command(self, update, context):
        """Gère la commande /jouer"""
        # Forcer l'état émotionnel JOIE
        previous_state = self.current_emotional_state
        self.current_emotional_state = "JOIE"
        
        games = [
            "Ze veux zouer à cache-cache! Toi compte et Simba se cache!",
            "On fait la chasse aux antilopes? Graouuu!",
            "Simba veut dessiner avec toi! On fait un lion?",
            "On zoue à chat perché? Simba court vite!"
        ]
        
        message = random.choice(games)
        update.message.reply_text(self._format_message_based_on_emotional_state(message))
        
        # Revenir à l'état précédent
        self.current_emotional_state = previous_state
    
    def handle_message(self, update, context):
        """Gère les messages texte reçus"""
        # Potentiellement changer d'état émotionnel
        self._maybe_change_emotional_state()
        
        user_message = update.message.text.lower()
        user_name = update.effective_user.first_name
        
        # Analyse simple du message pour déterminer une réponse
        if "calin" in user_message or "câlin" in user_message:
            response = f"Simba adore les câlins! Gros câlin pour {user_name}!"
            self.current_emotional_state = "CÂLIN"
        
        elif "jouer" in user_message or "jeu" in user_message:
            response = "Ze veux zouer! On fait quoi? Cache-cache? Chasse? Dessin?"
            self.current_emotional_state = "JOIE"
        
        elif "manger" in user_message or "faim" in user_message:
            response = "Simba a faim d'antilope! Miam miam!"
            self.current_emotional_state = "FAIM"
        
        elif "dormir" in user_message or "dodo" in user_message:
            response = "Simba est fatigué aussi... Ze veux ma babytière pour faire dodo..."
            self.current_emotional_state = "SOMMEIL"
        
        elif "cacher" in user_message or "cache" in user_message:
            response = "Simba est très fort pour cacher des choses! Surtout le téléphone de maman! Hihi!"
            self.current_emotional_state = "MALICE"
        
        else:
            # Réponses génériques selon l'état émotionnel
            generic_responses = {
                "JOIE": [
                    f"{user_name}! Toi veux zouer avec Simba?",
                    "Simba veut faire la fête! Graouuu!",
                    "Ze suis content de te voir!"
                ],
                "CURIOSITÉ": [
                    "Simba se demande ce que toi fais?",
                    "Pourquoi les antilopes courent vite?",
                    "Toi sais où est Nessie?"
                ],
                "MALICE": [
                    "Simba a caché quelque chose... Hihi!",
                    "Ze vais faire une surprise à maman!",
                    "Toi veux faire une bêtise avec Simba?"
                ],
                "CÂLIN": [
                    "Simba veut un câlin...",
                    "Ze t'aime fort fort fort!",
                    "Câlin de lion pour toi!"
                ],
                "FAIM": [
                    "Simba a faim! Toi as une antilope?",
                    "Le ventre de Simba fait GRAOU!",
                    "Ze veux manger maintenant!"
                ],
                "SOMMEIL": [
                    "Simba est fatigué... Bâillement de lion...",
                    "Ze veux ma babytière...",
                    "Dodo avec maman..."
                ],
                "JALOUSIE": [
                    "Toi zoues avec Nessie aussi?",
                    "Simba veut plus d'attention!",
                    "Regarde ce que Simba sait faire!"
                ]
            }
            
            response = random.choice(generic_responses.get(self.current_emotional_state, ["Graou!"]))
        
        # Envoyer la réponse formatée
        update.message.reply_text(self._format_message_based_on_emotional_state(response))
    
    def error_handler(self, update, context):
        """Gère les erreurs"""
        logger.error(f"Erreur: {context.error}")
    
    def send_initiative_message(self, chat_id):
        """Envoie un message d'initiative à un chat spécifique"""
        # Potentiellement changer d'état émotionnel
        self._maybe_change_emotional_state()
        
        # Messages d'initiative selon l'état émotionnel
        initiative_messages = {
            "JOIE": [
                "Graouuu! Simba veut zouer! Toi es là?",
                "Simba a trouvé un nouveau zeu! On essaie?",
                "Ze m'ennuie! On fait quelque chose de rigolo?"
            ],
            "CURIOSITÉ": [
                "Simba se demande ce que toi fais maintenant?",
                "Pourquoi le ciel est bleu? Simba réfléchit...",
                "Ze veux apprendre quelque chose nouveau!"
            ],
            "MALICE": [
                "Hihi! Simba a caché le téléphone de maman! Elle cherche partout!",
                "Ze prépare une surprise! Toi veux savoir?",
                "Simba a fait une petite bêtise... Mais c'est un secret!"
            ],
            "CÂLIN": [
                "Simba pense à toi et veut un câlin!",
                "Ze t'envoie un câlin de lion à distance! Tu le sens?",
                "Simba a besoin d'un gros câlin... Toi es là?"
            ],
            "FAIM": [
                "Le ventre de Simba fait GRAOU! Ze cherche des antilopes!",
                "Simba a tellement faim! Toi as mangé quoi?",
                "C'est l'heure du goûter pour Simba! Miam miam!"
            ],
            "SOMMEIL": [
                "Simba fait un gros bâillement... Ze suis fatigué...",
                "Ze vais chercher ma babytière pour faire dodo...",
                "Les yeux de Simba se ferment tout seuls... Dodo..."
            ],
            "JALOUSIE": [
                "Toi parles avec ChienChien aussi? Simba veut parler plus!",
                "Simba a fait un plus beau dessin que Nessie! Toi veux voir?",
                "Ze suis le plus fort des frères! Graou!"
            ]
        }
        
        message = random.choice(initiative_messages.get(self.current_emotional_state, ["Graou!"]))
        formatted_message = self._format_message_based_on_emotional_state(message)
        
        try:
            self.bot.send_message(chat_id=chat_id, text=formatted_message)
            logger.info(f"Message d'initiative envoyé: {formatted_message}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message d'initiative: {e}")
    
    def start(self):
        """Démarre le bot"""
        logger.info("Démarrage du bot Simba...")
        self.updater.start_polling()
        self.updater.idle()


def main():
    """Fonction principale"""
    # Charger le token depuis une variable d'environnement
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("Token Telegram non trouvé. Définissez la variable d'environnement TELEGRAM_TOKEN.")
        return
    
    # Créer et démarrer le bot
    simba_bot = SimbaBot(token)
    simba_bot.start()


if __name__ == "__main__":
    main()
