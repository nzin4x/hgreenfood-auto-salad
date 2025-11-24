import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import EmailScreen from './components/EmailScreen';
import VerifyScreen from './components/VerifyScreen';
import SetupScreen from './components/SetupScreen';
import DashboardScreen from './components/DashboardScreen';

function App() {
    const [screen, setScreen] = useState('loading');
    const [deviceFingerprint, setDeviceFingerprint] = useState(null);
    const [email, setEmail] = useState(null);
    const [user, setUser] = useState(null);

    useEffect(() => {
        const initFingerprint = async () => {
            if (window.FingerprintJS) {
                try {
                    const fp = await window.FingerprintJS.load();
                    const result = await fp.get();
                    const fingerprint = result.visitorId;
                    setDeviceFingerprint(fingerprint);
                    console.log('Device fingerprint:', fingerprint);
                    checkDevice(fingerprint);
                } catch (e) {
                    console.error('Fingerprint error:', e);
                    setScreen('email');
                }
            } else {
                console.error('FingerprintJS not loaded');
                setScreen('email');
            }
        };

        // Wait for script to load if needed
        if (window.FingerprintJS) {
            initFingerprint();
        } else {
            const checkInterval = setInterval(() => {
                if (window.FingerprintJS) {
                    clearInterval(checkInterval);
                    initFingerprint();
                }
            }, 100);
            setTimeout(() => clearInterval(checkInterval), 5000);
        }
    }, []);

    const checkDevice = async (fingerprint) => {
        try {
            const data = await api.checkDevice(fingerprint);
            if (data.authenticated) {
                setUser({
                    userId: data.userId,
                    email: data.email,
                    sessionToken: data.sessionToken
                });
                setScreen('dashboard');
            } else {
                setScreen('email');
            }
        } catch (error) {
            console.error('Device check error:', error);
            setScreen('email');
        }
    };

    const handleCodeSent = (emailInput) => {
        setEmail(emailInput);
        setScreen('verify');
    };

    const handleVerified = (data) => {
        if (data.hasAccount) {
            setUser({
                userId: data.userId,
                email: email, // or data.email if returned
                sessionToken: data.sessionToken
            });
            setScreen('dashboard');
        } else {
            setScreen('setup');
        }
    };

    const handleRegistered = (userId) => {
        setUser({
            userId: userId,
            email: email,
            sessionToken: 'new-session' // Ideally returned from register
        });
        setScreen('dashboard');
    };

    const handleLogout = () => {
        setUser(null);
        setEmail(null);
        setScreen('email');
    };

    return (
        <div className="container">
            <h1>🥗 HGreenFood</h1>
            <p className="subtitle">자동 예약 서비스</p>

            {screen === 'loading' && (
                <div className="loading">
                    <div className="spinner"></div>
                    <p style={{ marginTop: '15px', color: '#667eea' }}>처리 중...</p>
                </div>
            )}

            {screen === 'email' && (
                <EmailScreen onCodeSent={handleCodeSent} />
            )}

            {screen === 'verify' && (
                <VerifyScreen 
                    email={email} 
                    deviceFingerprint={deviceFingerprint} 
                    onVerified={handleVerified}
                    onBack={() => setScreen('email')}
                />
            )}

            {screen === 'setup' && (
                <SetupScreen 
                    email={email} 
                    deviceFingerprint={deviceFingerprint} 
                    onRegistered={handleRegistered}
                />
            )}

            {screen === 'dashboard' && user && (
                <DashboardScreen 
                    user={user} 
                    onLogout={handleLogout} 
                />
            )}
        </div>
    );
}

export default App;
