"""Package agent de l'application IRONPULSE.

Contient le cœur agentique :
  - tools.py : les fonctions appelables par le LLM (avec leurs schémas JSON)
  - agent.py : la boucle agent (raisonner → agir → observer → décider)

Le LLM ne touche jamais directement à la base : il choisit un tool, et c'est
le code Python de ce package qui l'exécute (voir diapo 8 du cahier des charges).
"""