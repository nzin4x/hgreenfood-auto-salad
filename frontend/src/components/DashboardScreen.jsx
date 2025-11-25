import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import SettingsModal from './SettingsModal';

export default function DashboardScreen({ user, onLogout }) {
    const [reservations, setReservations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [autoReservationEnabled, setAutoReservationEnabled] = useState(true);
    const [toggleLoading, setToggleLoading] = useState(false);
    const [immediateLoading, setImmediateLoading] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    const checkReservation = async () => {
        setLoading(true);
        setMessage(null);
        try {
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            
            // If tomorrow is Saturday (6), next business day is Monday (+2 = 8)
            // If tomorrow is Sunday (0), next business day is Monday (+1 = 1)
            // But let's just stick to "next day" for now, or maybe the API handles it?
            // The user said "today and tomorrow".
            // Let's fetch both.
            
            const todayStr = today.toISOString().split('T')[0];
            const tomorrowStr = tomorrow.toISOString().split('T')[0];

            const [todayData, tomorrowData] = await Promise.all([
                api.checkReservation(user.userId, todayStr),
                api.checkReservation(user.userId, tomorrowStr)
            ]);
            
            const newReservations = [];
            if (todayData.hasReservation && todayData.reservations.length > 0) {
                newReservations.push(...todayData.reservations.map(r => ({...r, label: '오늘'})));
            }
            if (tomorrowData.hasReservation && tomorrowData.reservations.length > 0) {
                newReservations.push(...tomorrowData.reservations.map(r => ({...r, label: '내일'})));
            }
            
            setReservations(newReservations);
        } catch (error) {
            console.error('Check reservation error:', error);
            setMessage({ text: '예약 정보를 불러올 수 없습니다', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleToggleAutoReservation = async () => {
        setToggleLoading(true);
        setMessage(null);
        try {
            const newState = !autoReservationEnabled;
            await api.toggleAutoReservation(user.userId, newState);
            setAutoReservationEnabled(newState);
            setMessage({ 
                text: newState ? '자동 예약이 활성화되었습니다' : '자동 예약이 비활성화되었습니다', 
                type: 'success' 
            });
        } catch (error) {
            console.error('Toggle error:', error);
            setMessage({ text: error.message || '설정 변경 실패', type: 'error' });
        } finally {
            setToggleLoading(false);
        }
    };

    const handleImmediateReservation = async () => {
        if (!confirm('지금 바로 예약을 진행하시겠습니까?')) {
            return;
        }
        
        setImmediateLoading(true);
        setMessage(null);
        try {
            const result = await api.makeImmediateReservation(user.userId);
            if (result.success) {
                setMessage({ text: `예약 성공: ${result.message}`, type: 'success' });
                checkReservation(); // Refresh reservations
            } else {
                setMessage({ text: `예약 실패: ${result.message}`, type: 'error' });
            }
        } catch (error) {
            console.error('Immediate reservation error:', error);
            setMessage({ text: error.message || '즉시 예약 실패', type: 'error' });
        } finally {
            setImmediateLoading(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (!confirm('진짜 삭제하시겠습니까?\n\n모든 예약 정보와 설정이 삭제되며 복구할 수 없습니다.')) {
            return;
        }
        
        try {
            await api.deleteAccount(user.userId);
            alert('계정이 삭제되었습니다.');
            onLogout();
        } catch (error) {
            console.error('Delete account error:', error);
            setMessage({ text: error.message || '계정 삭제 실패', type: 'error' });
        }
    };

    const handleSettingsSaved = () => {
        setShowSettings(false);
        setMessage({ text: '설정이 저장되었습니다', type: 'success' });
    };

    useEffect(() => {
        checkReservation();
    }, []);

    return (
        <div>
            <h2 style={{ marginBottom: '20px', color: '#667eea' }}>내 예약 정보</h2>
            
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                    <span style={{ color: '#666' }}>사용자</span>
                    <span style={{ fontWeight: 600 }}>{user.userId}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#666' }}>이메일</span>
                    <span style={{ fontWeight: 600 }}>{user.email}</span>
                </div>
            </div>


            {/* Auto-Reservation Toggle */}
            <div style={{ 
                marginBottom: '20px', 
                padding: '15px', 
                background: autoReservationEnabled ? '#e8f5e9' : '#fff3e0', 
                borderRadius: '8px',
                border: `2px solid ${autoReservationEnabled ? '#4caf50' : '#ff9800'}`
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <div style={{ fontWeight: 600, marginBottom: '5px' }}>
                            자동 예약 {autoReservationEnabled ? '활성화' : '비활성화'}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                            {autoReservationEnabled 
                                ? '매일 13:00에 자동으로 예약됩니다' 
                                : '자동 예약이 일시 중지되었습니다'}
                        </div>
                    </div>
                    <label style={{ 
                        position: 'relative', 
                        display: 'inline-block', 
                        width: '50px', 
                        height: '24px',
                        cursor: toggleLoading ? 'not-allowed' : 'pointer'
                    }}>
                        <input 
                            type="checkbox" 
                            checked={autoReservationEnabled}
                            onChange={handleToggleAutoReservation}
                            disabled={toggleLoading}
                            style={{ opacity: 0, width: 0, height: 0 }}
                        />
                        <span style={{
                            position: 'absolute',
                            cursor: toggleLoading ? 'not-allowed' : 'pointer',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: autoReservationEnabled ? '#4caf50' : '#ccc',
                            transition: '0.4s',
                            borderRadius: '24px'
                        }}>
                            <span style={{
                                position: 'absolute',
                                content: '',
                                height: '18px',
                                width: '18px',
                                left: autoReservationEnabled ? '29px' : '3px',
                                bottom: '3px',
                                backgroundColor: 'white',
                                transition: '0.4s',
                                borderRadius: '50%'
                            }}></span>
                        </span>
                    </label>
                </div>
            </div>

            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h3 style={{ margin: 0 }}>예약 현황</h3>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#666' }}>로딩 중...</div>
            ) : reservations.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
                    {reservations.map((res, index) => (
                        <div key={index} style={{ 
                            padding: '15px', 
                            border: '1px solid #eee', 
                            borderRadius: '8px',
                            background: '#fff',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                        }}>
                            <div style={{ 
                                display: 'inline-block', 
                                padding: '2px 8px', 
                                borderRadius: '12px', 
                                background: res.label === '오늘' ? '#e3f2fd' : '#f3e5f5',
                                color: res.label === '오늘' ? '#1976d2' : '#7b1fa2',
                                fontSize: '12px',
                                fontWeight: 600,
                                marginBottom: '8px'
                            }}>
                                {res.label} ({res.prvdDt ? res.prvdDt.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3') : ''})
                            </div>
                            <div style={{ fontWeight: 600, fontSize: '16px', marginBottom: '5px' }}>
                                {res.dispNm}
                            </div>
                            <div style={{ color: '#666', fontSize: '14px' }}>
                                {res.conerNm}
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div style={{ 
                    padding: '30px', 
                    textAlign: 'center', 
                    background: '#f8f9fa', 
                    borderRadius: '8px',
                    color: '#666' 
                }}>
                    예약 내역이 없습니다
                </div>
            )}
            
            {/* Refresh button removed */}
            <button 
                onClick={() => setShowSettings(true)} 
                style={{ 
                    marginTop: '10px', 
                    background: '#764ba2',
                    width: '100%'
                }}
            >
                ⚙️ 설정
            </button>
            <button onClick={onLogout} style={{ marginTop: '10px', background: '#6c757d' }}>
                로그아웃
            </button>
            
            {/* Delete Account Link */}
            <div style={{ textAlign: 'center', marginTop: '15px' }}>
                <a 
                    href="#" 
                    onClick={(e) => {
                        e.preventDefault();
                        handleDeleteAccount();
                    }}
                    style={{ 
                        fontSize: '11px', 
                        color: '#999', 
                        textDecoration: 'underline',
                        cursor: 'pointer'
                    }}
                >
                    개인정보 삭제
                </a>
            </div>

            {/* Settings Modal */}
            {showSettings && (
                <SettingsModal 
                    user={user} 
                    onClose={() => setShowSettings(false)}
                    onSaved={handleSettingsSaved}
                />
            )}
        </div>
    );
}
