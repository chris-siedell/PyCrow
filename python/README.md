# Crow Serial Protocol Implementation

Status: **experimental**

The Crow protocol is designed to allow a PC to control several microcontrollers using a single
serial line. The protocol itself has a simple half-duplex, command/response format with basic
error checking provided by Fletcher-16 checksums.

In Crow, the top-level software that generates commands is called a *client*. The client runs on the *host*, and
it passes the command to a *host implementation*. The host implementation creates a command packet
and sends it over the serial line. A *device implementation* receives the packet and then passes the command
to a *service* running on that *device*. The service performs the command and may send a response,
depending on the circumstances.

A *command* has the following properties:
- address: 1-31 for a specific device, or 0 to broadcast to all devices.
- port: 0-255, where open ports are registered to specific services.
- response expected: if true, the host will wait for a response; if false, the device must not respond.
- payload: 0-2047 bytes of binary data.

A *response* has just one property, the payload, which is also 0-2047 bytes of binary data.

----

This project contains a host implementation as well as a Crow admin client.

The Crow admin client can be used to send the commands `ping`, `echo`, `host_presence`,
`get_device_info`, `get_open_ports`, and `get_port_info`.

