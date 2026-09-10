"""The entry point of the process."""

# Den her robot er ikke koestyret: den henter HELE afdelingslisten én gang om
# dagen. Der er ikke noget at dele op i koeelementer, og et koeelement pr.
# afdeling ville goere en enkel liste til en byge af smaa kald.
from robot_framework import linear_framework
linear_framework.main()
