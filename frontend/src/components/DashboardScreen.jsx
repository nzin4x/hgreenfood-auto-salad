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
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const targetDate = tomorrow.toISOString().split('T')[0];

            const data = await api.checkReservation(user.userId, targetDate);
            
            if (data.hasReservation && data.reservations.length > 0) {
                setReservations(data.reservations);
            } else {
                setReservations([]);
            }
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
            
            <div id="reservationList">
                {loading ? (
                    <div className="loading">
                        <div className="spinner"></div>
                    </div>
                ) : reservations.length > 0 ? (
                    reservations.map((r, index) => (
                        <div key={index} className="reservation-card">
                            <h3>{r.dispNm || '예약됨'}</h3>
                            <div className="reservation-detail">
                                <span>날짜</span>
                                <span>{r.prvdDt ? r.prvdDt.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3') : '내일'}</span>
                            </div>
                            <div className="reservation-detail">
                                <span>코너</span>
                                <span>{r.conerNm || '알 수 없음'}</span>
                            </div>
                            <div className="reservation-detail">
                                <span>상태</span>
                                <span style={{ color: '#28a745' }}>✓ 예약 완료</span>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="message" style={{ textAlign: 'center', padding: '30px' }}>
                        <p style={{ fontSize: '48px', marginBottom: '10px' }}>📅</p>
                        <p style={{ color: '#666' }}>예약 대기 중입니다</p>
                        {autoReservationEnabled && (
                            <p style={{ color: '#999', fontSize: '12px', marginTop: '5px' }}>매일 13:00에 자동으로 예약됩니다</p>
                        )}
                        <button 
                            onClick={handleImmediateReservation} 
                            disabled={immediateLoading}
                            style={{ 
                                marginTop: '15px', 
                                background: '#ff9800',
                                opacity: immediateLoading ? 0.6 : 1
                            }}
                        >
                            {immediateLoading ? '예약 중...' : '지금 바로 예약하기'}
                        </button>
                    </div>
                )}
            </div>
            
            <button onClick={checkReservation} disabled={loading} style={{ marginTop: '20px' }}>
                예약 새로고침
            </button>
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
