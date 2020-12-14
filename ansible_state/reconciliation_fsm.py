from gevent_fsm.fsm import State, transitions

import yaml
from deepdiff import DeepDiff
from pprint import pprint
from .diff import ansible_state_diff, ansible_state_discovery, ansible_state_validation, convert_diff
from .messages import FSMState, DesiredState, Diff


class _Validate1(State):

    @transitions('Diff2')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Validate1'))

        # Trivial discovery
        # Assume the state is the same as new desired state

        monitor = controller.context

        monitor.operational_system_state = ansible_state_validation(monitor,
                                                                    monitor.secrets,
                                                                    monitor.project_src,
                                                                    monitor.new_desired_state,
                                                                    monitor.ran_rules,
                                                                    monitor.inventory,
                                                                    False)
        controller.changeState(Waiting)


Validate1 = _Validate1()


class _Discover1(State):

    @transitions('Diff2')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Discover1'))

        # Trivial discovery
        # Assume the state is the same as new desired state

        monitor = controller.context

        monitor.discovered_system_state = ansible_state_discovery(monitor.secrets,
                                                                  monitor.project_src,
                                                                  monitor.current_desired_state,
                                                                  monitor.new_desired_state,
                                                                  monitor.ran_rules,
                                                                  monitor.inventory,
                                                                  False)

        controller.changeState(Diff2)


Discover1 = _Discover1()


class _Help(State):

    def start(self, controller):
        controller.context.stream.put_message(FSMState('Help'))


Help = _Help()


class _Reconcile1(State):

    @transitions('Discover1')
    @transitions('Retry')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Reconcile1'))

        monitor = controller.context

        monitor.ran_rules = ansible_state_diff(monitor.secrets,
                                               monitor.project_src,
                                               monitor.current_desired_state,
                                               monitor.new_desired_state,
                                               monitor.rules,
                                               monitor.inventory,
                                               False)

        if True:
            controller.changeState(Discover1)
        else:
            controller.changeState(Retry)


Reconcile1 = _Reconcile1()


class _Reconcile2(State):

    @transitions('Discover1')
    @transitions('Retry')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Reconcile2'))

        monitor = controller.context

        result = ansible_state_diff(monitor.secrets,
                                    monitor.project_src,
                                    monitor.discovered_system_state,
                                    monitor.new_desired_state,
                                    monitor.rules,
                                    monitor.inventory,
                                    False)

        if result:
            controller.changeState(Discover1)
        else:
            controller.changeState(Retry)


Reconcile2 = _Reconcile2()


class _Reconcile3(State):

    @transitions('Discover1')
    @transitions('Retry')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Reconcile3'))

        monitor = controller.context

        result = ansible_state_diff(monitor.secrets,
                                    monitor.project_src,
                                    monitor.discovered_system_state,
                                    monitor.current_desired_state,
                                    monitor.rules,
                                    monitor.inventory,
                                    False)

        if result:
            controller.changeState(Discover2)
        else:
            controller.changeState(Retry)


Reconcile3 = _Reconcile3()


class _Waiting(State):

    def start(self, controller):
        controller.context.stream.put_message(FSMState('Waiting'))
        print("reconciliation_fsm buffered_messages", len(controller.context.buffered_messages))
        if not controller.context.buffered_messages.empty():
            controller.context.queue.put(controller.context.buffered_messages.get())

    @transitions('Diff1')
    def onDesiredState(self, controller, message_type, message):
        print('Waiting.onDesiredState')
        controller.context.new_desired_state = yaml.safe_load(message.desired_state)
        controller.context.stream.put_message(DesiredState(0, 0, controller.context.new_desired_state))
        controller.changeState(Diff1)

    @transitions('Diff1')
    def onSystemState(self, controller, message_type, message):
        print('Waiting.onSystemState')
        controller.context.discovered_system_state = yaml.safe_load(message.system_state)
        controller.changeState(Diff3)

    @transitions('Discover2')
    def onPoll(self, controller, message_type, message):
        controller.changeState(Discover2)


Waiting = _Waiting()


class _Diff1(State):

    @transitions('Reconcile1')
    @transitions('Waiting')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Diff1'))
        controller.context.diff = DeepDiff(controller.context.current_desired_state, controller.context.new_desired_state)
        pprint(controller.context.diff)
        controller.context.stream.put_message(Diff(convert_diff(controller.context.diff)))

        if controller.context.diff:
            controller.changeState(Reconcile1)
        else:
            controller.changeState(Waiting)


Diff1 = _Diff1()


class _Revert(State):

    def start(self, controller):
        controller.context.stream.put_message(FSMState('Revert'))

    @transitions('Help')
    def failure(self, controller, message_type, message):

        controller.changeState(Help)

    @transitions('Discover1')
    def success(self, controller, message_type, message):

        controller.changeState(Discover1)


Revert = _Revert()


class _Diff3(State):

    @transitions('Reconcile3')
    @transitions('Waiting')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Diff3'))
        controller.context.diff = DeepDiff(controller.context.discovered_system_state, controller.context.current_desired_state)
        print(controller.context.diff)

        if controller.context.diff:
            controller.changeState(Reconcile3)
        else:
            controller.changeState(Waiting)


Diff3 = _Diff3()


class _Discover2(State):

    @transitions('Diff3')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Discover2'))

        # Trivial discovery
        # Assume the state is the same as current desired state
        controller.context.discovered_system_state = controller.context.current_desired_state
        controller.changeState(Diff3)


Discover2 = _Discover2()


class _Start(State):

    @transitions('Waiting')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Start'))
        controller.changeState(Waiting)


Start = _Start()


class _Diff2(State):

    @transitions('Reconcile2')
    @transitions('Validate1')
    def start(self, controller):
        controller.context.stream.put_message(FSMState('Diff2'))
        controller.context.diff = DeepDiff(controller.context.new_desired_state, controller.context.discovered_system_state)
        print(controller.context.diff)
        controller.context.stream.put_message(Diff(convert_diff(controller.context.diff)))

        if controller.context.diff:
            controller.changeState(Reconcile2)
        else:
            controller.context.current_desired_state = controller.context.new_desired_state
            controller.changeState(Validate1)


Diff2 = _Diff2()


class _Retry(State):

    def start(self, controller):
        controller.context.stream.put_message(FSMState('Retry'))

    @transitions('Revert')
    def failure(self, controller, message_type, message):

        controller.changeState(Revert)

    @transitions('Discover1')
    def success(self, controller, message_type, message):

        controller.changeState(Discover1)


Retry = _Retry()