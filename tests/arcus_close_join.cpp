// Repro for libArcus ~Socket() aborting when the peer closed first:
// state becomes Closed/Error, close() returns without join, `delete thread` -> std::terminate.
// Exit 0 = fixed; SIGABRT (134) = bug present.
#include <Arcus/Socket.h>
#include <arpa/inet.h>
#include <chrono>
#include <cstdio>
#include <netinet/in.h>
#include <sys/socket.h>
#include <thread>
#include <unistd.h>

int main()
{
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    int one = 1;
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = 0;
    if (bind(srv, (sockaddr*)&a, sizeof a) || listen(srv, 1)) { perror("bind/listen"); return 2; }
    socklen_t l = sizeof a;
    getsockname(srv, (sockaddr*)&a, &l);

    auto* s = new Arcus::Socket();
    s->connect("127.0.0.1", ntohs(a.sin_port));
    int c = accept(srv, nullptr, nullptr);
    close(c); // peer goes away first, like Cura killing/closing the engine connection

    for (int i = 0; i < 100; ++i) // up to 10 s
    {
        auto st = s->getState();
        if (st == Arcus::SocketState::Closed || st == Arcus::SocketState::Error) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    auto st = s->getState();
    if (st != Arcus::SocketState::Closed && st != Arcus::SocketState::Error) { puts("socket never closed: test invalid"); return 3; }
    delete s; // aborts with the unpatched library
    puts("OK: socket destroyed cleanly");
    return 0;
}
