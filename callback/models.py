from django.db import models


class Player(models.Model):
    name = models.CharField(max_length=54)
    email = models.EmailField(max_length=54)
    date_create = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    name = models.CharField(max_length=254, default="")
    players = models.ManyToManyField(Player, blank=True, related_name="player_games")
    date_create = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
