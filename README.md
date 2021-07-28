## What is DRF Hooks?

drf-hooks is a fork of [Zapier's django-rest-hooks](https://github.com/zapier/django-rest-hooks), which is unfortunately not maintained anymore.

drf-hooks adds closer DRF integration by allowing you to specify DRF serializers to use for each model rather than requiring a `serialize_hook()` method on your models. It also allows hooks to specify custom headers to be added in the hook request (for instance for authentication).


## What are REST Hooks?

REST Hooks are fancier versions of webhooks. Traditional webhooks are usually
managed manually by the user, but REST Hooks are not! They encourage RESTful
access to the hooks (or subscriptions) themselves. Add one, two or 15 hooks for
any combination of event and URLs, then get notificatied in real-time by our
bundled threaded callback mechanism.

The best part is: by reusing Django's great signals framework, this library is
dead simple. Here's how to get started:

1. Add `'drf_hooks'` to installed apps in settings.py.
2. Define your `HOOK_EVENTS` and `HOOK_SERIALIZERS` in settings.py.
3. Start sending hooks!

Using our **built-in actions**, zero work is required to support *any* basic `created`,
`updated`, and `deleted` actions across any Django model. We also allow for
**custom actions** (IE: beyond **C**R**UD**) to be simply defined and triggered
for any model, as well as truly custom events that let you send arbitrary
payloads.

By default, this library will just POST Django's JSON serialization of a model,
but you can specify DRF serializers for each model in `HOOK_SERIALIZERS`.

*Please note:* this package does not implement any UI/API code, it only
provides a handy framework or reference implementation for which to build upon.
If you want to make a Django form or API resource, you'll need to do that yourself
(though we've provided some example bits of code below).

### Changelog

#### Version 0.1.0:

- Forked from zapier rest hooks
- Support for DRF serializers
- Custom hook header support


### Development

Running the tests for Django REST Hooks is very easy, just:

```
git clone https://github.com/am-flow/drf-hooks && cd drf-hooks
```

Next, you'll want to make a virtual environment (we recommend using virtualenvwrapper
but you could skip this we suppose) and then install dependencies:

```
mkvirtualenv drf-hooks
pip install -r requirements.txt
```

Now you can run the tests!

```
python runtests.py
```

### Requirements

* Python 3.7+ (tested on 3.7)
* Django 3.1+ (tested on 3.1)

### Installing & Configuring

We recommend pip to install drf-hooks:

```
pip install drf-hooks
```

Next, you'll need to add `drf_hooks` to `INSTALLED_APPS` and configure
your `HOOK_EVENTS` and `HOOK_SERIALIZER` setting:

```python
### settings.py ###

INSTALLED_APPS = (
    # other apps here...
    'drf_hooks',
)

HOOK_EVENTS = {
    # 'any.event.name': 'App.Model.Action' (created/updated/deleted)
    'book.added':       'bookstore.Book.created',
    'book.changed':     'bookstore.Book.updated+',
    'book.removed':     'bookstore.Book.deleted',
    # and custom events, no extra meta data needed
    'book.read':         'bookstore.Book.read',
    'user.logged_in':    None
}

HOOK_SERIALIZERS = {
    # 'App.Model': 'path.to.drf.serializer'
    'bookstore.Book': 'bookstore.serializers.BookSerializer',
}


### bookstore/models.py ###

class Book(models.Model):
    # NOTE: it is important to have a user property
    # as we use it to help find and trigger each Hook
    # which is specific to users. If you want a Hook to
    # be triggered for all users, add '+' to built-in Hooks
    # or pass user=None for custom_hook events
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    # maybe user is off a related object, so try...
    # user = property(lambda self: self.intermediary.user)

    title = models.CharField(max_length=128)
    pages = models.PositiveIntegerField()
    fiction = models.BooleanField()

    # ... other fields here ...

    def mark_as_read(self):
        # models can also have custom defined events
        from drf_hooks.signals import hook_event
        hook_event.send(
            sender=self.__class__,
            action='read',
            instance=self # the Book object
        )

### bookstore/serializers.py ###

class BookSerializer(serializers.ModelSerializer)
    class Meta:
        model = Book
        fields = '__all__'
```

For the simplest experience, you'll just piggyback off the standard ORM which will
handle the basic `created`, `updated` and `deleted` signals & events:

```python
>>> from django.contrib.auth.models import User
>>> from drf_hooks.models import Hook
>>> jrrtolkien = User.objects.create(username='jrrtolkien')
>>> hook = Hook(user=jrrtolkien,
                event='book.added',
                target='http://example.com/target.php')
>>> hook.save()     # creates the hook and stores it for later...
>>> from bookstore.models import Book
>>> book = Book(user=jrrtolkien,
                title='The Two Towers',
                pages=327,
                fiction=True)
>>> book.save()     # fires off 'bookstore.Book.created' hook automatically
...
```

> NOTE: If you try to register an invalid event hook (not listed on HOOK_EVENTS in settings.py)
you will get a **ValidationError**.

Now that the book has been created, `http://example.com/target.php` will get:

```
POST http://example.com/target.php \
    -H Content-Type: application/json \
    -d '{"hook": {
           "id":      123,
           "event":   "book.added",
           "target":  "http://example.com/target.php"},
         "data": {
           "title":   "The Two Towers",
           "pages":   327,
           "fiction": true}}'
```

You can continue the example, triggering two more hooks in a similar method. However,
since we have no hooks set up for `'book.changed'` or `'book.removed'`, they wouldn't get
triggered anyways.

```python
...
>>> book.title += ': Deluxe Edition'
>>> book.pages = 352
>>> book.save()     # would fire off 'bookstore.Book.updated' hook automatically
>>> book.delete()   # would fire off 'bookstore.Book.deleted' hook automatically
```

You can also fire custom events with an arbitrary payload:

```python
from drf_hooks.signals import raw_hook_event

user = User.objects.get(id=123)
raw_hook_event.send(
    sender=None,
    event_name='user.logged_in',
    payload={
        'username': user.username,
        'email': user.email,
        'when': datetime.datetime.now().isoformat()
    },
    user=user # required: used to filter Hooks
)
```


### How does it work?

Django has a stellar [signals framework](https://docs.djangoproject.com/en/dev/topics/signals/), all
drf-hooks does is register to receive all `post_save` (created/updated) and `post_delete` (deleted)
signals. It then filters them down by:

1. Which `App.Model.Action` actually have an event registered in `settings.HOOK_EVENTS`.
2. After it verifies that a matching event exists, it searches for matching Hooks via the ORM.
3. Any Hooks that are found for the User/event combination get sent a payload via POST.


### How would you interact with it in the real world?

**Let's imagine for a second that you've plugged REST Hooks into your API**.
One could definitely provide a user interface to create hooks themselves via
a standard browser & HTML based CRUD interface, but the real magic is when
the Hook resource is part of an API.

The basic target functionality is:

```shell
POST http://your-app.com/api/hooks?username=me&api_key=abcdef \
    -H Content-Type: application/json \
    -d '{"target":    "http://example.com/target.php",
         "event":     "book.added"}'
```

Now, whenever a Book is created (either via an ORM, a Django form, admin, etc...),
`http://example.com/target.php` will get:

```shell
POST http://example.com/target.php \
    -H Content-Type: application/json \
    -d '{"hook": {
           "id":      123,
           "event":   "book.added",
           "target":  "http://example.com/target.php"},
         "data": {
           "title":   "Structure and Interpretation of Computer Programs",
           "pages":   657,
           "fiction": false}}'
```

*It is important to note that drf-hooks will handle all of this hook
callback logic for you automatically.*

But you can stop it anytime you like with a simple:

```
DELETE http://your-app.com/api/hooks/123?username=me&api_key=abcdef
```

#### Builtin serializers, views, urls

drf-hooks comes with a `HookSerializer`, `HookViewSet` and an urlconf already baked in.
You can use as many or as little of these as you like. 
To use all of the above, add the following to your `urls.py`:


```python

urlpatterns = [
    # other urls
    path('hooks', include('drf_hooks.urls')),
]
```

### Extend the Hook model:

The default `Hook` model fields can be extended using the `AbstractHook` model.
This can also be used to customize other behavior such as hook lookup, serialization, delivery, etc.

For example, to add a `is_active` field on your hooks and customize hook finding so that only active hooks are fired:

```python
### settings.py ###

HOOK_CUSTOM_MODEL = 'app_label.ActiveHook'

### models.py ###

from django.db import models
from drf_hooks.models import AbstractHook

class ActiveHook(AbstractHook):
    is_active = models.BooleanField(default=True)

    @classmethod
    def find_hooks(cls, event_name, payload, user=None):
        hooks = super().find_hooks(event_name, payload, user=user)
        return hooks.filter(is_active=True)
```

You can also use this to override hook delivery. 
drf-hooks uses a simple Threading pool to deliver your hooks, but you may want to use some kind of background worker.
Here's an example using Celery:

### Some gotchas:

```python
### settings.py ###

HOOK_CUSTOM_MODEL = 'app_label.CeleryHook'

### tasks.py ###

from celery.task import Task

import requests

class DeliverTask(Task):
    max_retries = 5

    def run(self, hook_id, payload, **kwargs):
        """Deliver the payload to the hook target"""
        hook = CeleryHook.objects.get(id=hook_id)
        try:
            response = requests.post(
                url=hook.target,
                data=payload,
                headers=hook.headers
            )
            if response.status_code >= 500:
                response.raise_for_status()
        except requests.ConnectionError:
            delay_in_seconds = 2 ** self.request.retries
            self.retry(countdown=delay_in_seconds)

class CeleryHook(AbstractHook):
    def deliver_hook(self, serialized_hook):
        DeliverTask.apply_async(hook_id=self.id, payload=serialized_hook)
```

We also don't handle retries or cleanup. Generally, if you get a `410` or
a bunch of `4xx` or `5xx`, you should delete the Hook and let the user know.
