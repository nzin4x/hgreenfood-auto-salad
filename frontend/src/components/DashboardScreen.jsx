import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

export default function DashboardScreen({ user, onLogout }) {
    const [reservations, setReservations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);

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
                        <p style={{ color: '#999', fontSize: '12px', marginTop: '5px' }}>매일 13:00에 자동으로 예약됩니다</p>
                    </div>
                )}
            </div>
            
            <button onClick={checkReservation} disabled={loading} style={{ marginTop: '20px' }}>
                예약 새로고침
            </button>
            <button onClick={onLogout} style={{ marginTop: '10px', background: '#6c757d' }}>
                로그아웃
            </button>
        </div>
    );
}
