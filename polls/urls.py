from django.urls import path

from . import views

urlpatterns = [
    path('', views.form, name='index'),
    path('access', views.index, name='chatbox'),
    path('howto', views.howto, name='howto'),
    path('caseid',views.caseid, name='caseid'),
    path('interview',views.interview, name='interview'),
    path('mention',views.mention, name='mention')
    
]