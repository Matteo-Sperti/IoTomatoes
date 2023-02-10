FROM nodered/node-red:latest

RUN npm install node-red
RUN npm install node-red-dashboard
RUN npm install node-red-contrib-ui-led
RUN npm install node-red-contrib-ui-media
RUN npm install node-red-node-ui-table
RUN npm install node-red-contrib-users
RUN npm install node-red-contrib-simpletime
RUN npm install node-red-contrib-moving-average

# Copy the Node-RED flows
COPY ./flows.json /data/flows.json

RUN mkdir -p /data/lib/ui-media/lib/Logo
COPY ./IoTomatoes_logo.png /data/lib/ui-media/lib/Logo/IoTomatoes_logo.png