FROM alpine

RUN apk --update add git less openssh && \
    rm -rf /var/lib/apt/lists/* && \
    rm /var/cache/apk/*

ARG branch=master

# Cache buster -- make sure everything after this is never cached
ADD http://worldtimeapi.org/api/timezone/Europe/London.txt /tmp/bustcache
RUN git clone --single-branch --branch ${branch} https://github.com/enigmampc/enigma-p2p.git

# Save Git commit hash of this build into /git_commit.
RUN git -C /enigma-p2p/ rev-parse HEAD > /git_commit