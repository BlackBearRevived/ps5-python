# Hello Python app

This is the first per-app bundle example.

```text
apps/hello/
├── app.json
├── main.py
├── lib/greeting.py
└── assets/message.txt
```

Deploy it from WSL with:

```sh
PS5_HOST=192.0.2.10 make ps5-app APP=apps/hello
```
