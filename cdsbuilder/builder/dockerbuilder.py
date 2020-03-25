from concurrent.futures import ThreadPoolExecutor

import docker
from docker.errors import APIError
from docker.utils import kwargs_from_env
from traitlets import Dict, Unicode, Any
from tornado import gen
from tornado.log import app_log
from datetime import datetime

from jupyterhub.user import User

from cdsbuilder.builder.builders import Builder, BuildException


class DockerBuilder(Builder):

    user = Any()

    @property
    def client(self):
        """single global client instance"""
        cls = self.__class__
        if cls._client is None:
            kwargs = {"version": "auto"}
            if self.tls_config:
                kwargs["tls"] = docker.tls.TLSConfig(**self.tls_config)
            kwargs.update(kwargs_from_env())
            kwargs.update(self.client_kwargs)
            client = docker.APIClient(**kwargs)
            cls._client = client
        return cls._client

    tls_config = Dict(
        config=True,
        help="""Arguments to pass to docker TLS configuration.
        See docker.client.TLSConfig constructor for options.
        """,
    )

    client_kwargs = Dict(
        config=True,
        help="Extra keyword arguments to pass to the docker.Client constructor.",
    )

    _client = None

    def _docker(self, method, *args, **kwargs):
        """wrapper for calling docker methods
        to be passed to ThreadPoolExecutor
        """
        m = getattr(self.client, method)
        return m(*args, **kwargs)

    def docker(self, method, *args, **kwargs):
        """Call a docker method in a background thread
        returns a Future
        """
        return self.executor.submit(self._docker, method, *args, **kwargs)

    _executor = None

    @property
    def executor(self):
        """single global executor"""
        cls = self.__class__
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(1)
        return cls._executor

    repo_prefix = Unicode(default_value='cdsuser').tag(config=True)

    @gen.coroutine
    def start(self, dashboard, db):
        """Start the dashboard

        Returns:
          (str, int): the (ip, port) where the Hub can connect to the server.

        """

        app_log.info('Starting start function')

        self._build_pending = True

        source_spawner = dashboard.source_spawner

        object_id = source_spawner.state.get('object_id',None)

        app_log.debug('Docker object_id is {}'.format(object_id))

        if object_id is None:
            raise BuildException('No docker object specified in spawner state')

        source_container = yield self.docker('inspect_container', object_id)

        if source_container is None:
            raise BuildException('No docker object returned as source container')

        reponame = '{}/{}'.format(self.repo_prefix, dashboard.urlname)

        tag = datetime.today().strftime('%Y%m%d-%H%M%S')

        image_name = '{}:{}'.format(reponame, tag)

        app_log.info('Committing Docker image {}'.format(image_name))

        yield self.docker('commit', object_id, repository=reponame, tag=tag)

        self.log.info('Finished commit of Docker image {}:{}'.format(reponame, tag))

        ### Start a new server

        new_server_name = '{}-{}'.format(dashboard.urlname, tag)

        dashboard_user = User(dashboard.user)

        if not self.allow_named_servers:
            raise BuildException(400, "Named servers are not enabled.")
        if (
            self.named_server_limit_per_user > 0
            and new_server_name not in dashboard_user.orm_spawners
        ):
            named_spawners = list(dashboard_user.all_spawners(include_default=False))
            if self.named_server_limit_per_user <= len(named_spawners):
                raise BuildException(
                    "User {} already has the maximum of {} named servers."
                    "  One must be deleted before a new server can be created".format(
                        dashboard_user.name, self.named_server_limit_per_user
                    ),
                )
        spawner = dashboard_user.spawners[new_server_name]
        pending = spawner.pending

        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            # set _spawn_pending flag to prevent races while we wait
            spawner._spawn_pending = True
            try:
                state = yield spawner.poll_and_notify()
            finally:
                spawner._spawn_pending = False

        new_server_options = {'image': image_name}

        return (new_server_name, new_server_options)
        


    allow_named_servers = True # TODO take from main app config
    named_server_limit_per_user = 10

    @gen.coroutine
    def stop(self, now=False):
        """Stop the single-user server

        If `now` is False (default), shutdown the server as gracefully as possible,
        e.g. starting with SIGINT, then SIGTERM, then SIGKILL.
        If `now` is True, terminate the server immediately.

        The coroutine should return when the single-user server process is no longer running.

        Must be a coroutine.
        """
        raise NotImplementedError(
            "Override in subclass. Must be a Tornado gen.coroutine."
        )


    @gen.coroutine
    def poll(self):
        pass
