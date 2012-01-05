from forum.models import *
from forum.forms import *
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import Context, RequestContext
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
import datetime
from time import strftime
from django.db.models import Q

from django.core.mail import send_mail, EmailMessage

from urllib import urlopen
import json

def homepage(request):

    venue_id = "4e9700536da11364e6ee330d"
    
    # venue_id = "4b4f64eff964a520a40427e3"
    # EZ's across the street, testing from home purposes only
    
    oauth_token = "ZZTN1TVTCWF0NBI12JW3PRFOHGT5PVWX4CI2SIBXZQ0UCNOB"
    url = "https://api.foursquare.com/v2/venues/" + venue_id + "/herenow?oauth_token=" + oauth_token + "&v=20111212"

    f = urlopen(url)
    f = f.read()    
    j = json.loads(f)
    
    members_herenow = []
    fsusers_herenow = []

    for item in j['response']['hereNow']['items']:
        fname = item['user']['firstName']
        lname = item['user']['lastName']
        
        try:
            user = User.objects.get(Q(first_name = fname)&Q(last_name = lname))
            members_herenow.append(user)
        except:
            fsusers_herenow.append(fname + " " + lname)

    return render_to_response(
        'global/homepage.html',
        {
            'title': "Welcome to Geekdom.",
            'subtitle': "",
            'members_herenow' : members_herenow,
            'fsusers_herenow' : fsusers_herenow,
        }, 
        context_instance=RequestContext(request)
    )




# view all forums
def all_forums(request):
  forums = Forum.objects.annotate(models.Max("thread__reply__created_on")).order_by("-thread__reply__created_on__max")
  return render_to_response(
    'forum/forum_list.html', 
    {
      'title': "All Forums",
      'subtitle': "Listing all currently open forums",
      'forums' : forums,
    }, 
    context_instance=RequestContext(request)
  )




# view forum
def view_forum(request, forum_id):
  forum = Forum.objects.get(id=forum_id)
  return render_to_response(
    'forum/forum_view.html', 
    {
      'title': forum.name,
      'subtitle': forum.description,
      'forum' : forum,
    }, 
    context_instance=RequestContext(request)
  )




def new_forum(request):
  if request.method == 'POST':
    form = ForumForm(request.POST)
    if form.is_valid():
      forum = form.save()
      message = "Forum successfully created!"
      messages.add_message(request, messages.SUCCESS, message)
      return HttpResponseRedirect('/forums/' + str(forum.id))
  else:
    form = ForumForm()
  
  return render_to_response(
    'global/modelform.html',
    {
      'title': 'Create a new forum',
      'form' : form
    }, 
    context_instance=RequestContext(request))




# create a new thread in a forum
def create_thread(request, forum_id):
  forum = Forum.objects.get(id = forum_id)
  if request.method == 'POST':
    form = ThreadForm(request.POST)
    form.instance.forum_id = forum_id
    form.instance.user_id = request.user.id
    if form.is_valid():
      thread = form.save()
      message = "Thread successfully created!"
      messages.add_message(request, messages.SUCCESS, message)
      return HttpResponseRedirect('/forums/' + str(forum_id) + "/" + str(thread.id))
  else:
    form = ThreadForm()
  
  return render_to_response(
    'global/modelform.html',
    {
      'title': 'Create a new thread in ' + forum.name,
      'form':form
    }, 
    context_instance=RequestContext(request))
  

# view thread
def view_thread(request, forum_id, thread_id):
  thread = Thread.objects.get(id = thread_id)
  form = ReplyForm()
  return render_to_response(
    'forum/thread_view.html', 
    {
      'title': thread.subject,
      'subtitle': thread.user.userprofile.cname() + " on " + thread.created_on.strftime("%m/%d/%Y at %I:%M %p"),
      'thread' : thread,
      'form' : form,
    }, 
    context_instance=RequestContext(request)
  )

# create reply
def reply_to_thread(request, forum_id, thread_id):
  if request.method == 'POST':
      form = ReplyForm(request.POST)
      form.instance.thread_id = thread_id
      form.instance.user_id = request.user.id
      if form.is_valid():
          reply = form.save()
          message = "Reply added!"
          messages.add_message(request, messages.SUCCESS, message)
          return HttpResponseRedirect('/forums/' + forum_id + '/' + thread_id)
  else:
    message = "Something broke! Whoops!"
    messages.add_message(request, messages.ERROR, message)
    return HttpResponseRedirect('/forums/' + forum_id + '/' + thread_id)




###############
# event views #
###############

# view all upcoming events
def upcoming_events(request):
  now = datetime.datetime.now()
  events = Event.objects.filter(starts_at__gte = now)
  return render_to_response(
    'forum/event_list.html', 
    {
      'title': "All upcoming events",
      'subtitle': "Events starting soonest first",
      'events' : events,
    }, 
    context_instance=RequestContext(request)
  )

# view a project
def view_event(request, event_id):
  event = Event.objects.get(id=event_id)

  return render_to_response(
    'forum/event_view.html', 
    {
      'title': event.name,
      'event' : event,
    }, 
    context_instance=RequestContext(request)
  )

# rsvp for event
@login_required
def rsvp_event(request, event_id):
  event = Event.objects.get(id=event_id)
  event.attendees.add(request.user)
  event.save()
  message = "You have successfully RSVP'd for this event!"
  messages.add_message(request, messages.SUCCESS, message)
  return HttpResponseRedirect("/events/" + str(event.id))

# unrsvp for event
@login_required
def unrsvp_event(request, event_id):
  event = Event.objects.get(id=event_id)
  event.attendees.remove(request.user)
  event.save()
  message = "You have successfully UN-RSVP'd for this event!"
  messages.add_message(request, messages.WARNING, message)
  return HttpResponseRedirect("/events/" + str(event.id))

# events im attending
def events_attending(request):
  now = datetime.datetime.now()
  events = Event.objects.filter(attendees = request.user).filter(starts_at__gte = now)
  return render_to_response(
    'forum/event_list.html', 
    {
      'title': "Events you've RSVP'd for",
      'subtitle': "Events starting soonest first",
      'events' : events,
    }, 
    context_instance=RequestContext(request)
  )

# events from my forums
def events_recommended(request):
  now = datetime.datetime.now()
  events = Event.objects.filter(forum__members = request.user)
  return render_to_response(
    'forum/event_list.html', 
    {
      'title': "Events recommended for you",
      'subtitle': "Events starting soonest first",
      'events' : events,
    }, 
    context_instance=RequestContext(request)
  )

@login_required
def new_event(request):
  if request.method == 'POST':
      
    if request.user.is_superuser:
        form = AdminEventForm(request.POST)
    else:
        form = EventForm(request.POST)
        
    if form.is_valid():
      event = form.save()
      
      if event.forum.members.count() > 0:
        count = 0
        for user in event.forum.members.all():
          subject = "[geekdom] New Event - " + event.name

          message = """Hey you, """ + user.get_full_name() + """!
            A new event has been posted to """ + event.forum.name + """.

            """ + event.name + """
            """ + str(event.starts_at) + """ until """ + str(event.ends_at) + """
            """ + event.description + """

            Go to: http://geekdom.awesomemonster.com/events/""" + str(event.id) + """ for more information.

            --            
            The Geekdom Team

            """

          send_mail(subject, message, 'events@geekdom.com', [user.email], fail_silently=False)

          count = count + 1
          
        message = "Event successfully created! Notified " + str(count) + " users of the " + event.forum.name + " forum."
        messages.add_message(request, messages.SUCCESS, message)
      return HttpResponseRedirect('/events/' + str(event.id))

      
  else:
    if request.user.is_superuser:
        form = AdminEventForm()
    else:
        form = EventForm()
        
  return render_to_response(
    'global/modelform.html',
    {
      'title': 'Create a new event',
      'form' : form
    }, 
    context_instance=RequestContext(request))






def subscribe_to_forum(request, forum_id):
  forum = Forum.objects.get(id = forum_id)
  forum.members.add(request.user)
  forum.save()
  message = "You are now subscribed to \"" + forum.name + "\""
  messages.add_message(request, messages.SUCCESS, message)
  return HttpResponseRedirect("/forums/" + str(forum.id))




def unsubscribe_from_forum(request, forum_id):
  forum = Forum.objects.get(id = forum_id)
  forum.members.remove(request.user)
  forum.save()
  message = "You are now unsubscribed to \"" + forum.name + "\""
  messages.add_message(request, messages.WARNING, message)
  return HttpResponseRedirect("/forums/" + str(forum.id))








def mail_forum_users(request, forum_id):
  if not request.user.is_superuser: return HttpResponseNotFound()
  
  forum = Forum.objects.get(id = forum_id)

  if request.method == 'POST':
    form = ForumMailForm(request.POST)
    if form.is_valid():
      count = 0
      for user in forum.members.all():
        subject = "[geekdom] " + request.POST.get('subject')
        message = request.POST.get('message')
        send_mail(subject, message, 'notifications@geekdom.com', [user.email], fail_silently=False)
        count = count + 1
          
      message = "Message sent to the " + str(count) + " users of the " + forum.name + " forum."
      messages.add_message(request, messages.SUCCESS, message)
      return HttpResponseRedirect('/forums/' + str(forum.id))
                
  else:
    form = ForumMailForm()

  return render_to_response(
    'global/modelform.html',
    {
      'title': 'Send a message to: ' + forum.name,
      'form' : form
    }, 
    context_instance=RequestContext(request))

  
  
  
  
def send_member_message(request, user_id):
    
    user = User.objects.get(id = user_id)
    
    instructions = "Send a message to a member. Your full name, phone number and email will be included as the signature of the message."
    
    if request.method == 'POST':
        form = UserMailForm(request.POST)
        if form.is_valid():
            subject = "[geekdom] Message from " + request.user.get_full_name()
            collected_message = request.POST.get('message') + """
            --
            """ + request.user.get_full_name() + """
            """ + request.user.userprofile.phone_number + """
            """ + request.user.email
            
            email = EmailMessage(
                subject,
                collected_message, 
                "internal-mail@geekdom.com", 
                [user.email], 
                [],
                headers = {'Reply-To': request.user.email}
                ).send()
            
            message = "Message sent to " + user.get_full_name() + "."
            messages.add_message(request, messages.SUCCESS, message)
            return HttpResponseRedirect('/members/' + str(user.id))
                
    else:
        form = UserMailForm()

    return render_to_response(
        'global/modelform.html',
        {
         'title': 'Mail: ' + user.get_full_name(),
         'form' : form,
         'instructions' : instructions,
         }, 
    context_instance=RequestContext(request))
      
      
      