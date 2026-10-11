# Génération de la page web

La page https://jfb4plai.com/atelier-ia/vibecoding/ est générée depuis `../README.md`.

```
python3 build/md2html.py README.md build/template.html <landing-jfb4plai>/atelier-ia/vibecoding/index.html
cp exemple-generateur-prompt.html <landing-jfb4plai>/atelier-ia/vibecoding/
```

À relancer après chaque modification du guide.
