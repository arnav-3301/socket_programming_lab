#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cstring>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
using namespace std;

vector<vector<int>> adj = {{}};

string HOST = "0.0.0.0";
int PORT = 5000;
string FN = "";


vector<vector<int>> buildmatrix(string fn){
    vector<vector<int>> rows;
    string line;
    ifstream file(fn);

    if(!file.is_open())
        throw runtime_error("Cannot open configuration file");

    while(getline(file,line)){
        if(line.empty() || line[0] == '#') continue;
        stringstream ss(line);
        vector<int> costs;
        int x;
        while(ss>>x) costs.push_back(x);
        if(!costs.empty()) rows.push_back(costs);
    }

    int n=rows.size()+1;
    vector<vector<int>> adj(n,vector<int>(n,-1));

    for(int i=0;i<n;i++) adj[i][i]=0;

    for(int i=0;i<n;i++)
        for(int j=i+1;j<n;j++)
            adj[i][j] = adj[j][i] = rows[i][j-i-1];

    cout<<"Adjacency Matrix: "<<endl;
    for(int i=0;i<adj.size();i++){
        for(int j=0;j<adj[i].size();j++){
            if(adj[i][j]!=-1) cout<<" "<<adj[i][j]<<"\t";
            else cout<<adj[i][j]<<"\t";
        }
        cout << endl;
    }
    cout<<endl;

    return adj;
}

struct Connection {
    char node_id;
    int socket;
    string ip;
    int port;

    // pair<string,int> address;
};




void sendall(vector<Connection> connections, vector<vector<int>> adj){
    for(int i=0;i<(int)connections.size();i++){
        char buffer[1024];
        int offset = 0;

        uint16_t count = 0;
        for(int j=0;j<(int)adj.size();j++){
            if(adj[i][j] != -1) count++;
        }

        uint16_t count_net = htons(count);
        memcpy(buffer + offset,&count_net,2);
        offset += 2;

        for(int j=0;j<(int)adj.size();j++){
            if(adj[i][j] != -1){
                buffer[offset++] = 'A' + j;

                uint32_t ip_net;
                inet_pton(AF_INET,connections[j].ip.c_str(),&ip_net);
                memcpy(buffer + offset,&ip_net,4);
                offset += 4;

                uint16_t port_net = htons(connections[j].port);
                memcpy(buffer + offset,&port_net,2);
                offset += 2;

                int32_t cost_net = htonl(adj[i][j]);
                memcpy(buffer + offset,&cost_net,4);
                offset += 4;
            }
        }

        send(connections[i].socket,buffer,offset,0);
    }
}
void closeall(vector<Connection> connections){
    for(int i=0;i<(int)connections.size();i++){
        close(connections[i].socket);
    }
}





int main(int argc,char* argv[]){

    if(argc!=4){
        std::cerr<<"Usage: "<<argv[0]<<" <ip addr> <port> <config file>"<<endl;
        return 1;
    }

    HOST = argv[1];
    try{
        PORT = stoi(argv[2]);}
    catch(...){
        cerr<<"Invalid Port Number";
        return 1;
    }
    FN = argv[3];

    if(PORT<1 || PORT>65535) {
        cerr<<"Error: Port must be between 1 and 65535"<<endl;
        return 1;
    }

    adj = buildmatrix(FN);

    int n = adj.size();

    int ser = socket(AF_INET,SOCK_STREAM,0);

    if(ser<0){
        perror("socket");
        return 1;
    }

    sockaddr_in server_addr{};  
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    // inet_pton(AF_INET,HOST.c_str(),&server_addr.sin_addr);

    if(inet_pton(AF_INET,HOST.c_str(),&server_addr.sin_addr)!=1){
        cerr << "Invalid server IP address\n";
        close(ser);
        return 1;
    }

    // bind(ser,(sockaddr*)&server_addr,sizeof(server_addr));
    // listen(ser,5);

    if(bind(ser,(sockaddr*)&server_addr,sizeof(server_addr))<0){
        perror("bind");
        close(ser);
        return 1;
    }

    if(listen(ser,n+1)<0){
        perror("listen");
        close(ser);
        return 1;
    }

    int num_of_vn = 0;
    vector<Connection> connections;

    while(num_of_vn < n) {
        sockaddr_in addr{};
        socklen_t len = sizeof(addr);
        int conn = accept(ser,(sockaddr*)&addr,&len);
        if(conn<0){perror("accept");continue;}

        // string msg;
        // char ch;
        // while(recv(conn,&ch,1,0)==1 && ch!='\n') msg += ch;

        // string ip;
        // int port;
        // stringstream ss(msg);
        // getline(ss,ip,',');
        // ss>>port;

        // char node_id = 'A' + num_of_vn;
        // connections.push_back({node_id,conn,ip,port});

        // cout << "Connected to node " << node_id << ", UDP IP: " << ip << ", UDP Port: " << port << '\n';

        char buf[6];
        recv(conn,buf,6,MSG_WAITALL);
        uint32_t ip_net;
        memcpy(&ip_net,buf,4);
        char ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &ip_net, ip_str, INET_ADDRSTRLEN);
        string ip = string(ip_str);

        uint16_t port_net;
        memcpy(&port_net,buf+4,2);
        int port = ntohs(port_net);


        char node_id = 'A' + num_of_vn;
        connections.push_back({node_id,conn,ip,port});
        
        cout << "Connected to node " << node_id << ", UDP IP: " << ip << ", UDP Port: " << port << '\n';

        num_of_vn++;
    }

    sendall(connections,adj);

    while(true){
        sleep(6);
        vector<vector<int>> adj1 = {{}};
        adj1 = buildmatrix(FN);
        bool change = false;

        for(int i=0;i<n;i++){
            for(int j=0;j<n;j++){
                if(adj[i][j]!=adj1[i][j]){
                    change = true;
                    break;
                }
            }
            if(change) break;
        }

        if(change){adj=adj1;sendall(connections,adj1);}

    }

    closeall(connections);
    close(ser);
}
