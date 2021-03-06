#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import vte

class GTK_Main(object):
  
  def __init__(self, debug=False):
    # save init values
    self.debug=debug
    self.fullscreen = False # this is technicaly not consistant as it is not chnaged on system uests
    self.pipeline = None
    
    # setup the window
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.window.set_title("SDP 6")
    self.window.set_default_size(600, 400)
        
    self.window.set_events(gtk.gdk.KEY_PRESS_MASK|gtk.gdk.KEY_RELEASE_MASK)
    self.window.connect("key_press_event", self.on_key_press)
    self.window.connect("key_release_event", self.on_key_release)
    self.window.connect("destroy", self.clean_quit)
    
    # add widgets
    root_widget = gtk.HBox()
    self.window.add(root_widget)
    
    vbox_rightpanel = gtk.VBox()
    root_widget.add(vbox_rightpanel)
    
    vbox_leftpanel = gtk.VBox()
    vbox_leftpanel.set_size_request(150, 0)
    root_widget.add(vbox_leftpanel)
    
    hbox_rightpanel_top = gtk.HBox()
    vbox_rightpanel.add(hbox_rightpanel_top)
    
    hbox_rightpanel_bottom = gtk.HBox()
    hbox_rightpanel_bottom.set_size_request(0, 100)
    vbox_rightpanel.add(hbox_rightpanel_bottom)
    
    hbox_leftpanel_feed = gtk.HBox()
    hbox_leftpanel_feed.set_size_request(150, 0)
    vbox_leftpanel.add(hbox_leftpanel_feed)
    
    self.button = gtk.ToggleButton("Start Feed")
    self.button.connect("clicked", self.start_stop)
    hbox_leftpanel_feed.add(self.button)
    
    vbox_leftpanel_feed_radio = gtk.VBox()
    hbox_leftpanel_feed.add(vbox_leftpanel_feed_radio)
    
    radio1 = gtk.RadioButton(group=None, label="Real")
    radio1.set_active(True)
    radio1.connect("toggled", self.radio_feed_change)
    vbox_leftpanel_feed_radio.add(radio1)
    
    self.feed_radio = "real"
    
    radio2 = gtk.RadioButton(group=radio1, label="Test")
    vbox_leftpanel_feed_radio.add(radio2)
    
    self.button_fixcolour = gtk.ToggleButton("Fix Colour")
    hbox_leftpanel_feed.add(self.button_fixcolour)
    
    for i in range(0, 5):
      button = gtk.Button("test "+str(i))
      vbox_leftpanel.add(button)
    
    self.movie_window = gtk.DrawingArea()
    hbox_rightpanel_top.add(self.movie_window)
    
    self.movie_window2 = gtk.DrawingArea()
    hbox_rightpanel_top.add(self.movie_window2)
    
    self.vte = vte.Terminal()
    self.vte.connect ("child-exited", self.respawn_vte)
    self.vte.fork_command()
    hbox_rightpanel_bottom.add(self.vte)
    
    self.window.show_all()
    
  def respawn_vte(self, widget):
    self.vte.fork_command()
  
  def on_key_press(self, widget, data=None):
    print widget
    print data
    if widget == self.vte:
      return
    print "click"
    if data.keyval == 65362: # up
        print "Up"
    elif data.keyval == 65364: # down
        print "Down"
    elif data.keyval == 65361: # left
        print "Left"
    elif data.keyval == 65363: # right
        print "Right"
    elif data.keyval == 65307: # Esc
        self.clean_quit()
    elif data.string == "s":
        print "Stop!"
    elif data.string == "f":
      if self.fullscreen:
        self.window.unfullscreen()
        self.fullscreen = False
      else:
        self.window.fullscreen()
        self.fullscreen = True
    else:
        if self.debug:
            print "DEBUG:\n\tevent: '{event}'\n\tkeyval: '{keyval}'\n\tstring: '{str_}'"\
            .format(event="key_press_unknown_key", keyval=data.keyval, str_=data.string)
  
  def on_key_release(self, widget, data=None):
    print "un-click"
  
  def clean_quit(self, widget=None, data=None):
    print "Clean Quit"
    gtk.main_quit()
    
  def start_stop(self, widget, data=None):
    if self.pipeline == None:
      self.start_feed()
    else:
      self.stop_feed()
            
  def on_message(self, bus, message):
    t = message.type
    if t == gst.MESSAGE_EOS: # end of feed
      self.stop_feed()
    elif t == gst.MESSAGE_ERROR:
      err, debug = message.parse_error()
      print "Error: %s" % err, debug
      self.stop_feed()
  
  def on_sync_message(self, bus, message):
    if message.structure is None:
      return
    message_name = message.structure.get_name()
    if message_name == "prepare-xwindow-id":
      imagesink = message.src
      imagesink.set_property("force-aspect-ratio", True)
      gtk.gdk.threads_enter()
      imagesink.set_xwindow_id(self.movie_window.window.xid)
      gtk.gdk.threads_leave()
  
  def on_sync_message2(self, bus, message):
    if message.structure is None:
      return
    message_name = message.structure.get_name()
    if message_name == "prepare-xwindow-id":
      imagesink = message.src
      imagesink.set_property("force-aspect-ratio", True)
      gtk.gdk.threads_enter()
      imagesink.set_xwindow_id(self.movie_window2.window.xid)
      gtk.gdk.threads_leave()
  
  def start_feed(self):
    self.build_pipeline()
    self.build_pipeline2()
    self.pipeline.set_state(gst.STATE_PLAYING)
    self.pipeline2.set_state(gst.STATE_PLAYING)
    self.button.set_label("Stop")
    self.button.set_active(True)
  
  def stop_feed(self):
    self.pipeline.set_state(gst.STATE_NULL)
    self.pipeline2.set_state(gst.STATE_NULL)
    self.pipeline = None
    self.button.set_label("Start Feed")
    self.button.set_active(False)
  
  def build_pipeline(self):
    # make the gstreamer pipline
    self.pipeline = gst.Pipeline("webcam")
    
    if self.feed_radio == "test":
      source = gst.element_factory_make("videotestsrc", "webcam-source")
    else:
      source = gst.element_factory_make("v4l2src", "webcam-source")
    
    videosink = gst.element_factory_make("autovideosink", "video-output")
    
    if self.button_fixcolour.get_active():
      colorspace = gst.element_factory_make("ffmpegcolorspace", "colorspace")
      self.pipeline.add(source, colorspace, videosink)
      gst.element_link_many(source, colorspace, videosink)
    else:
      self.pipeline.add(source, videosink)
      gst.element_link_many(source, videosink)

    bus = self.pipeline.get_bus()
    bus.add_signal_watch()
    bus.enable_sync_message_emission()
    bus.connect("message", self.on_message)
    bus.connect("sync-message::element", self.on_sync_message)
  
  def build_pipeline2(self):
    # make the gstreamer pipline
    self.pipeline2 = gst.Pipeline("webcam 2")
    
    if self.feed_radio != "test":
      source = gst.element_factory_make("videotestsrc", "webcam-source")
    else:
      source = gst.element_factory_make("v4l2src", "webcam-source")
    
    videosink = gst.element_factory_make("autovideosink", "video-output")
    
    if self.button_fixcolour.get_active():
      colorspace = gst.element_factory_make("ffmpegcolorspace", "colorspace")
      self.pipeline2.add(source, colorspace, videosink)
      gst.element_link_many(source, colorspace, videosink)
    else:
      self.pipeline2.add(source, videosink)
      gst.element_link_many(source, videosink)

    bus = self.pipeline2.get_bus()
    bus.add_signal_watch()
    bus.enable_sync_message_emission()
    bus.connect("message", self.on_message)
    bus.connect("sync-message::element", self.on_sync_message2)
  
  def radio_feed_change(self, widget, data=None):
    if self.feed_radio == "real":
      self.feed_radio = "test"
    else:
      self.feed_radio = "real"
  

if __name__ == '__main__':
    GTK_Main(debug=True)
    gtk.gdk.threads_init()
    gtk.main()

