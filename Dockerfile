FROM debian:11

WORKDIR /root/app

ADD docker-entrypoint.sh /bin/docker-entrypoint.sh

ENV DISPLAY :99
ENV DEBIAN_FRONTEND noninteractive

USER root

ADD build /root/build/

RUN cd /root/build &&\
    chmod +x /bin/docker-entrypoint.sh &&\
    apt update &&\
    apt install -y unzip curl wget ffmpeg mkvtoolnix xvfb python3 python3-pip supervisor &&\
    curl -L https://raw.githubusercontent.com/tj/n/master/bin/n -o n &&\
    bash n lts &&\
    wget -q https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_100.0.1185.29-1_amd64.deb &&\
    dpkg -i microsoft-edge-stable_100.0.1185.29-1_amd64.deb || true &&\
    apt install -f -y &&\
    wget https://msedgedriver.azureedge.net/100.0.1185.29/edgedriver_linux64.zip &&\
    unzip edgedriver_linux64.zip &&\
    mv msedgedriver /usr/bin/msedgedriver &&\
    pip3 install -r /root/build/requirements.txt &&\
    npm -g i minyami &&\
    apt autoremove -y &&\
    apt autoclean &&\
    rm -rf /var/lib/apt/lists/* &&\
    rm -rf /root/build

ADD app /root/app/

ADD supervisor.conf /etc/supervisor/conf.d/

ENTRYPOINT ["/bin/docker-entrypoint.sh"]

#ENTRYPOINT ["/usr/bin/supervisord","--nodaemon"] 
