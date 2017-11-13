#!/usr/bin/python
# -*- coding: utf-8 -*-


import threading
import sys
import os
import roslib
import rospy
import actionlib
sys.path.append(os.path.join(os.path.dirname(__file__), '../actions'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../conditions'))
import Conditions

from importlib import import_module
from AbstractAction import AbstractAction
from pnp_msgs.msg import PNPActionFeedback, PNPResult, PNPAction
from pnp_msgs.srv import PNPCondition, PNPConditionResponse

roslib.load_manifest('pnp_ros')
PKG = 'pnp_ros'
NODE = 'pnpactionserver'
action_instances = {}


## find the action implementation
def find_action_implementation(action_name):
    try:
        action_class = getattr(import_module(action_name), action_name)
        if issubclass(action_class, AbstractAction):
            return action_class
        else:
            rospy.logwarn("class " + action_class + " must inherit from AbstractAction")
    except (ImportError, AttributeError):
        rospy.logwarn("action " + action_name + " not implemented")



def startAction(goalhandler):
    goal = goalhandler.get_goal()
    print "Starting " + goal.name + " " + goal.params

    # search for an implementation of the action
    action = find_action_implementation(goal.name)

    if action:
        # accept the goal
        goalhandler.set_accepted()

        # Instantiate the action
        action_instance = action(goalhandler, goal.params)

        # add action instance to the dict
        action_instances.update({
            goal.id : action_instance
        })

        # start the action
        action_instances[goal.id].start_action()


def cancelAction(goalhandler):
    goal = goalhandler.get_goal()
    print "Terminating " + goal.name + " " + goal.params
    # accept the goal
    goalhandler.set_accepted()

    # stop the action
    if goal.id in action_instances:
        action_instances[goal.id].stop_action()


class PNPActionServer(object):
    #  create messages that are used to publish feedback/result
    _feedback = PNPActionFeedback()
    _result = PNPResult()

    def __init__(self, name):
        self._action_server_name = name
        self._as = actionlib.ActionServer(self._action_server_name,
                                          PNPAction,
                                          self.execute_cb,
                                          auto_start=False)
        self._as.start()
        rospy.loginfo('%s: Action Server started' % self._action_server_name)

    def execute_cb(self, goalhandler):
        r = rospy.Rate(4)
        # init running
        self._feedback.feedback = 'running...'
        goalhandler.publish_feedback(self._feedback)
        goal = goalhandler.get_goal()

        # publish info to the console for the user
        rospy.loginfo('%s: Starting action %s %s' %
                      (self._action_server_name, goal.name, goal.params))
        if goal.function == 'start':
            # start executing the action
            startAction(goalhandler)
        elif goal.function == 'interrupt':
            #  print '### Interrupt ',goal.name
            cancelAction(goalhandler)
        elif goal.function == 'end':
            #  print '### End ',goal.name
            cancelAction(goalhandler)

def find_condition_implementation(cond_name):
    try:
        cond_func = getattr(Conditions, cond_name)
        return cond_func
    except AttributeError:
        rospy.logwarn("Condition " + cond_name + " not implemented")
        return None

## Callback which take the requests for checking conditions
def handle_PNPConditionEval(req):
    global condvalue
    cond_elems = req.cond.split("_")
    cond = cond_elems[0]
    params = cond_elems[1:]
    print 'Eval condition: ', cond

    # find implementation of the condition
    cond_func = find_condition_implementation(cond)

    if cond_func:
        cond_value = cond_func(params)
        return PNPConditionResponse(cond_value)
    else:
        # return False if not implemented..
        return PNPConditionResponse(0)

if __name__ == '__main__':
    rospy.init_node(NODE)
    rospy.set_param('robot_name', 'dummy')

    PNPActionServer("PNP")
    rospy.Service('PNPConditionEval',
                  PNPCondition,
                  handle_PNPConditionEval)

    rospy.spin()
