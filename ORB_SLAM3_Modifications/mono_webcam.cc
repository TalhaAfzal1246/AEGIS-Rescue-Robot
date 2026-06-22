// #include<iostream>
// #include<algorithm>
// #include<fstream>
// #include<chrono>
// #include<opencv2/core/core.hpp>
// #include<opencv2/highgui/highgui.hpp>
// #include<System.h>

// using namespace std;

// int main(int argc, char **argv)
// {
//     if(argc != 3) {
//         cerr << endl << "Usage: ./mono_webcam path_to_vocabulary path_to_settings" << endl;
//         return 1;
//     }

//     // Initialize SLAM system
//     ORB_SLAM3::System SLAM(argv[1], argv[2], ORB_SLAM3::System::MONOCULAR, true);

//     // --- NETWORK STREAM CONNECTION ---
//     // CHANGE THIS IP TO YOUR NAMESERVER IP!
//     string video_stream_url = "http://172.20.16.1:5000/video";

//     // cv::CAP_FFMPEG forces Linux to handle the network stream properly
//     cv::VideoCapture cap(video_stream_url, cv::CAP_FFMPEG);

//     if(!cap.isOpened()) {
//         cerr << "Failed to connect to Windows Python Server at " << video_stream_url << endl;
//         return 1;
//     }

//     cout << "Connected to Windows Webcam Stream! Point it at a room with good lighting!" << endl;
//     // ---------------------------------

//     cv::Mat frame;
   
//     // NEW: Initialize a perfect synthetic clock starting at 0 seconds
//     double tframe = 0.0;

//     while(true) {
//         cap >> frame;
//         if(frame.empty()) {
//             cerr << "Stream dropped!" << endl;
//             break;
//         }
//         tframe += 1.0 / 30.0;

//         // Generate a timestamp for the frame
//         //double tframe = std::chrono::duration_cast<std::chrono::duration<double>>(std::chrono::system_clock::now().time_since_epoch()).count();

//         // Inject the frame into ORB-SLAM3
//         // Grab the 4x4 Pose Matrix from the SLAM engine
//         Sophus::SE3f Tcw = SLAM.TrackMonocular(frame, tframe);

//         // Extract the camera's location relative to the World Origin (0,0,0)
//         Eigen::Vector3f twc = Tcw.inverse().translation();

//         // Print the real-time X, Y, Z coordinates to the terminal (in meters)
//         cout << "[AEGIS POS] X: " << twc[0] << " | Y: " << twc[1] << " | Z: " << twc[2] << " \r" << flush;
//     }

//     SLAM.Shutdown();
//     return 0;
// }




// #include <iostream>
// #include <algorithm>
// #include <fstream>
// #include <chrono>
// #include <opencv2/core/core.hpp>
// #include <opencv2/highgui/highgui.hpp>
// #include <System.h>

// // --- NEW NETWORK & THREAD HEADERS ---
// #include <sys/socket.h>
// #include <netinet/in.h>
// #include <arpa/inet.h>
// #include <unistd.h>
// #include <thread>
// #include <mutex>
// #include <cstring>
// #include <cstdio>
// // ------------------------------------

// using namespace std;

// // --- AEGIS HARDWARE TELEMETRY GLOBALS ---
// float global_x = 0.0;
// float global_y = 0.0;
// float global_theta = 0.0;
// std::mutex physics_mutex;

// // This function runs in the background and constantly catches Python packets
// void PhysicsListenerThread() {
//     int sockfd;
//     struct sockaddr_in servaddr;

//     sockfd = socket(AF_INET, SOCK_DGRAM, 0);
//     memset(&servaddr, 0, sizeof(servaddr));

//     servaddr.sin_family = AF_INET; 
//     servaddr.sin_addr.s_addr = INADDR_ANY; 
//     servaddr.sin_port = htons(9090); // Listening on port 9090!

//     bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr));

//     char buffer[1024];
//     while(true) {
//         int n = recvfrom(sockfd, (char *)buffer, 1024, MSG_WAITALL, nullptr, nullptr);
//         if (n > 0) {
//             buffer[n] = '\0';
            
//             float temp_x, temp_y, temp_theta;
//             // Parse the "X,Y,Theta" string
//             if (sscanf(buffer, "%f,%f,%f", &temp_x, &temp_y, &temp_theta) == 3) {
//                 // Lock the memory for a microsecond to safely update it
//                 std::lock_guard<std::mutex> lock(physics_mutex);
//                 global_x = temp_x;
//                 global_y = temp_y;
//                 global_theta = temp_theta;
//             }
//         }
//     }
// }
// // ----------------------------------------

// int main(int argc, char **argv)
// {
//     if(argc != 3) {
//         cerr << endl << "Usage: ./mono_webcam path_to_vocabulary path_to_settings" << endl;
//         return 1;
//     }

//     // NEW: Start the UDP listener in a separate background thread immediately!
//     std::thread physics_thread(PhysicsListenerThread);
//     physics_thread.detach(); 

//     // Initialize SLAM system
//     ORB_SLAM3::System SLAM(argv[1], argv[2], ORB_SLAM3::System::MONOCULAR, true);

//     // --- NETWORK STREAM CONNECTION ---
//     // CHANGE THIS IP TO YOUR NAMESERVER IP!
//     string video_stream_url = "http://172.20.16.1:5000/video";

//     // cv::CAP_FFMPEG forces Linux to handle the network stream properly
//     cv::VideoCapture cap(video_stream_url, cv::CAP_FFMPEG);

//     if(!cap.isOpened()) {
//         cerr << "Failed to connect to Windows Python Server at " << video_stream_url << endl;
//         return 1;
//     }

//     cout << "Connected to Windows Webcam Stream! Point it at a room with good lighting!" << endl;
//     // ---------------------------------

//     cv::Mat frame;
    
//     // Initialize a perfect synthetic clock starting at 0 seconds
//     double tframe = 0.0;

//     while(true) {
//         cap >> frame;
//         if(frame.empty()) {
//             cerr << "Stream dropped!" << endl;
//             break;
//         }
        
//         // Guarantee time never goes backwards (stops Map Resets)
//         tframe += 1.0 / 30.0;

//         // Inject the frame into ORB-SLAM3
//         Sophus::SE3f Tcw = SLAM.TrackMonocular(frame, tframe);

//         // Extract the camera's location relative to the World Origin (0,0,0)
//         Eigen::Vector3f twc = Tcw.inverse().translation();

//         // Safely pull the live hardware physics data
//         float current_x, current_y, current_theta;
//         {
//             std::lock_guard<std::mutex> lock(physics_mutex);
//             current_x = global_x;
//             current_y = global_y;
//             current_theta = global_theta;
//         }

//         // Print BOTH brains to the terminal side-by-side!
//         cout << "[SLAM] Z: " << twc[2] << "m | [WHEELS] X: " << current_x << " Y: " << current_y << " Th: " << current_theta << "        \r" << flush;
//     }

//     SLAM.Shutdown();
//     return 0;
// }





// #include <iostream>
// #include <algorithm>
// #include <fstream>
// #include <chrono>
// #include <cmath> // NEW: Required for square root math
// #include <opencv2/core/core.hpp>
// #include <opencv2/highgui/highgui.hpp>
// #include <System.h>

// // --- NETWORK & THREAD HEADERS ---
// #include <sys/socket.h>
// #include <netinet/in.h>
// #include <arpa/inet.h>
// #include <unistd.h>
// #include <thread>
// #include <mutex>
// #include <cstring>
// #include <cstdio>
// // ------------------------------------

// using namespace std;

// // --- AEGIS HARDWARE TELEMETRY GLOBALS ---
// float global_x = 0.0;
// float global_y = 0.0;
// float global_theta = 0.0;
// std::mutex physics_mutex;

// // Background thread to catch ESP32 physics packets
// void PhysicsListenerThread() {
//     int sockfd;
//     struct sockaddr_in servaddr;

//     sockfd = socket(AF_INET, SOCK_DGRAM, 0);
//     memset(&servaddr, 0, sizeof(servaddr));

//     servaddr.sin_family = AF_INET; 
//     servaddr.sin_addr.s_addr = INADDR_ANY; 
//     servaddr.sin_port = htons(9090); 

//     bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr));

//     char buffer[1024];
//     while(true) {
//         int n = recvfrom(sockfd, (char *)buffer, 1024, MSG_WAITALL, nullptr, nullptr);
//         if (n > 0) {
//             buffer[n] = '\0';
//             float temp_x, temp_y, temp_theta;
//             if (sscanf(buffer, "%f,%f,%f", &temp_x, &temp_y, &temp_theta) == 3) {
//                 std::lock_guard<std::mutex> lock(physics_mutex);
//                 global_x = temp_x;
//                 global_y = temp_y;
//                 global_theta = temp_theta;
//             }
//         }
//     }
// }
// // ----------------------------------------

// int main(int argc, char **argv)
// {
//     if(argc != 3) {
//         cerr << endl << "Usage: ./mono_webcam path_to_vocabulary path_to_settings" << endl;
//         return 1;
//     }

//     // Start the UDP listener in a separate background thread
//     std::thread physics_thread(PhysicsListenerThread);
//     physics_thread.detach(); 

//     // Initialize SLAM system
//     ORB_SLAM3::System SLAM(argv[1], argv[2], ORB_SLAM3::System::MONOCULAR, true);

//     // --- NETWORK STREAM CONNECTION ---
//     string video_stream_url = "http://172.20.16.1:5000/video";
//     cv::VideoCapture cap(video_stream_url, cv::CAP_FFMPEG);

//     if(!cap.isOpened()) {
//         cerr << "Failed to connect to Windows Python Server at " << video_stream_url << endl;
//         return 1;
//     }

//     cout << "Connected to Windows Webcam Stream! FUSION ENGINE ONLINE." << endl;

//     cv::Mat frame;
//     double tframe = 0.0;

//     // --- FUSION STATE VARIABLES ---
//     Eigen::Vector3f prev_twc = Eigen::Vector3f::Zero();
//     float prev_wheel_x = 0.0;
//     float prev_wheel_y = 0.0;
//     float global_scale = 1.0; // Start with a 1:1 baseline
//     const float alpha = 0.05; // EMA Trust Factor (0.05 is highly smooth)
//     bool first_frame = true;

//     while(true) {
//         cap >> frame;
//         if(frame.empty()) {
//             cerr << "Stream dropped!" << endl;
//             break;
//         }
        
//         tframe += 1.0 / 30.0;

//         // Visual tracking
//         Sophus::SE3f Tcw = SLAM.TrackMonocular(frame, tframe);
//         Eigen::Vector3f twc = Tcw.inverse().translation();

//         // Hardware tracking
//         float current_x, current_y, current_theta;
//         {
//             std::lock_guard<std::mutex> lock(physics_mutex);
//             current_x = global_x;
//             current_y = global_y;
//             current_theta = global_theta;
//         }

//         // --- SENSOR FUSION ENGINE ---
//         if (first_frame) {
//             prev_twc = twc;
//             prev_wheel_x = current_x;
//             prev_wheel_y = current_y;
//             first_frame = false;
//         } else {
//             // 1. Calculate absolute physical distance moved (Wheels)
//             float dx_wheel = current_x - prev_wheel_x;
//             float dy_wheel = current_y - prev_wheel_y;
//             float d_wheel = sqrt((dx_wheel * dx_wheel) + (dy_wheel * dy_wheel));

//             // 2. Calculate visual distance moved (SLAM)
//             float dx_slam = twc[0] - prev_twc[0];
//             float dz_slam = twc[2] - prev_twc[2]; 
//             float d_slam = sqrt((dx_slam * dx_slam) + (dz_slam * dz_slam));

//             // 3. Dynamic Scale Locking
//             // Only update scale if the robot actually moved (prevents divide by zero)
//             if (d_slam > 0.001 && d_wheel > 0.001) {
//                 float s_instant = d_wheel / d_slam;
                
//                 // Sanity Check: Reject insane optical glitches
//                 if (s_instant > 0.1 && s_instant < 10.0) {
//                     global_scale = (alpha * s_instant) + ((1.0 - alpha) * global_scale);
//                 }
//             }

//             // 4. Calculate Final Real-World Fused Coordinates
//             float fused_x = twc[0] * global_scale;
//             float fused_y = twc[2] * global_scale; // Z in camera is Y on the floor

//             // Output the ultimate AEGIS coordinates
//             cout << "[AEGIS SYSTEM] Real X: " << fused_x << "m | Real Y: " << fused_y << "m | Locked Scale Factor: " << global_scale << "        \r" << flush;

//             // Update state for next frame
//             prev_twc = twc;
//             prev_wheel_x = current_x;
//             prev_wheel_y = current_y;
//         }
//     }

//     SLAM.Shutdown();
//     return 0;
// }









#include <iostream>
#include <algorithm>
#include <fstream>
#include <chrono>
#include <cmath> // Required for square root math
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <System.h>
#include <MapDrawer.h> // --- NEW: Required for 3D Holographic Pins ---

// --- NETWORK & THREAD HEADERS ---
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <thread>
#include <mutex>
#include <cstring>
#include <cstdio>
// ------------------------------------

using namespace std;

// --- AEGIS HARDWARE TELEMETRY GLOBALS ---
float global_x = 0.0;
float global_y = 0.0;
float global_theta = 0.0;
int global_hazard_state = 0; // NEW: Holds the YOLO hazard code
std::mutex physics_mutex;

// Background thread to catch ESP32 physics packets
void PhysicsListenerThread() {
    int sockfd;
    struct sockaddr_in servaddr;

    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    memset(&servaddr, 0, sizeof(servaddr));

    servaddr.sin_family = AF_INET; 
    servaddr.sin_addr.s_addr = INADDR_ANY; 
    servaddr.sin_port = htons(9090); 

    bind(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr));

    char buffer[1024];
    while(true) {
        int n = recvfrom(sockfd, (char *)buffer, 1024, MSG_WAITALL, nullptr, nullptr);
        if (n > 0) {
            buffer[n] = '\0';
            float temp_x, temp_y, temp_theta;
            int temp_hazard = 0;
            
            // --- UPDATED: Now parses X, Y, Theta, AND Hazard Code ---
            if (sscanf(buffer, "%f,%f,%f,%d", &temp_x, &temp_y, &temp_theta, &temp_hazard) >= 3) {
                std::lock_guard<std::mutex> lock(physics_mutex);
                global_x = temp_x;
                global_y = temp_y;
                global_theta = temp_theta;
                global_hazard_state = temp_hazard;
            }
        }
    }
}
// ----------------------------------------

int main(int argc, char **argv)
{
    if(argc != 3) {
        cerr << endl << "Usage: ./mono_webcam path_to_vocabulary path_to_settings" << endl;
        return 1;
    }

    // Start the UDP listener in a separate background thread
    std::thread physics_thread(PhysicsListenerThread);
    physics_thread.detach(); 

    // Initialize SLAM system
    ORB_SLAM3::System SLAM(argv[1], argv[2], ORB_SLAM3::System::MONOCULAR, true);

    // --- NETWORK STREAM CONNECTION ---
    string video_stream_url = "http://172.20.16.1:5000/video";
    cv::VideoCapture cap(video_stream_url, cv::CAP_FFMPEG);

    if(!cap.isOpened()) {
        cerr << "Failed to connect to Windows Python Server at " << video_stream_url << endl;
        return 1;
    }

    cout << "Connected to Windows Webcam Stream! FUSION ENGINE ONLINE." << endl;

    cv::Mat frame;
    double tframe = 0.0;

    // --- FUSION STATE VARIABLES ---
    Eigen::Vector3f prev_twc = Eigen::Vector3f::Zero();
    float prev_wheel_x = 0.0;
    float prev_wheel_y = 0.0;
    float global_scale = 1.0; // Start with a 1:1 baseline
    const float alpha = 0.05; // EMA Trust Factor (0.05 is highly smooth)
    bool first_frame = true;

    while(true) {
        cap >> frame;
        if(frame.empty()) {
            cerr << "Stream dropped!" << endl;
            break;
        }
        
        tframe += 1.0 / 30.0;

        // Visual tracking
        Sophus::SE3f Tcw = SLAM.TrackMonocular(frame, tframe);
        Eigen::Vector3f twc = Tcw.inverse().translation();

        // Hardware tracking
        float current_x, current_y, current_theta;
        int current_hazard;
        {
            std::lock_guard<std::mutex> lock(physics_mutex);
            current_x = global_x;
            current_y = global_y;
            current_theta = global_theta;
            current_hazard = global_hazard_state; // Safely pull the hazard state
        }

        // --- SENSOR FUSION ENGINE ---
        if (first_frame) {
            prev_twc = twc;
            prev_wheel_x = current_x;
            prev_wheel_y = current_y;
            first_frame = false;
        } else {
            // 1. Calculate absolute physical distance moved (Wheels)
            float dx_wheel = current_x - prev_wheel_x;
            float dy_wheel = current_y - prev_wheel_y;
            float d_wheel = sqrt((dx_wheel * dx_wheel) + (dy_wheel * dy_wheel));

            // 2. Calculate visual distance moved (SLAM)
            float dx_slam = twc[0] - prev_twc[0];
            float dz_slam = twc[2] - prev_twc[2]; 
            float d_slam = sqrt((dx_slam * dx_slam) + (dz_slam * dz_slam));

            // 3. Dynamic Scale Locking
            // Only update scale if the robot actually moved (prevents divide by zero)
            if (d_slam > 0.001 && d_wheel > 0.001) {
                float s_instant = d_wheel / d_slam;
                
                // Sanity Check: Reject insane optical glitches
                if (s_instant > 0.1 && s_instant < 10.0) {
                    global_scale = (alpha * s_instant) + ((1.0 - alpha) * global_scale);
                }
            }

            // 4. Calculate Final Real-World Fused Coordinates
            float fused_x = twc[0] * global_scale;
            float fused_y = twc[2] * global_scale; // Z in camera is Y on the floor

            // --- DROP 3D HAZARD PIN ---
            static Eigen::Vector3f last_drop_pos = Eigen::Vector3f::Zero();
            
            if (current_hazard > 0) {
                // Check distance to prevent dropping 1,000 cubes in the exact same spot
                float dist_from_last = (twc - last_drop_pos).norm();
                
                // Must move at least 1 meter away from the last pin to drop a new one
                if (dist_from_last > 1.0 || last_drop_pos == Eigen::Vector3f::Zero()) { 
                    global_hazards_mutex.lock();
                    // Drop the pin at the camera's current 3D world location
                    global_aegis_hazards.push_back({twc[0], twc[1], twc[2], (float)current_hazard});
                    global_hazards_mutex.unlock();
                    last_drop_pos = twc;
                    cout << endl; 
                    if (current_hazard == 1) {
                        cout << "🚨 [TACTICAL ALERT] CONSCIOUS VICTIM MAPPED AT X: " << twc[0] << "m | Y: " << twc[2] << "m 🚨" << endl;
                    } else if (current_hazard == 2) {
                        cout << "🚨 [CRITICAL ALERT] UNCONSCIOUS VICTIM MAPPED AT X: " << twc[0] << "m | Y: " << twc[2] << "m 🚨" << endl;
                    } else if (current_hazard == 3) {
                        cout << "🔥 [HAZARD ALERT] FIRE MAPPED AT X: " << twc[0] << "m | Y: " << twc[2] << "m 🔥" << endl;
                    }
                }
            }
            // --------------------------

            // Output the ultimate AEGIS coordinates
            cout << "[AEGIS SYSTEM] Real X: " << fused_x << "m | Real Y: " << fused_y << "m | Locked Scale Factor: " << global_scale << "        \r" << flush;

            // Update state for next frame
            prev_twc = twc;
            prev_wheel_x = current_x;
            prev_wheel_y = current_y;
        }
    }

    SLAM.Shutdown();
    return 0;
}
