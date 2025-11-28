import React, { useState } from 'react';
import { api } from '../services/api';
import MenuPreferenceSelector from './MenuPreferenceSelector';

export default function SetupScreen({ email, deviceFingerprint, onRegistered }) {
    const [formData, setFormData] = useState({
        userId: '',
        password: '',
        menuSeq: '샌,샐,빵,헬,닭',
        floorNm: '5층'
    });
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.id]: e.target.value
        });
    };

    const handleMenuSeqChange = (newSeq) => {
        setFormData({
            ...formData,
            menuSeq: newSeq
        });
    };

    const handleRegister = async () => {
        const { userId, password, menuSeq, floorNm } = formData;

        if (!userId || !password || !menuSeq || !floorNm) {
            setMessage({ text: '모든 필드를 입력하세요', type: 'error' });
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            await api.registerUser({
                ...formData,
                email,
                deviceFingerprint
            });
            onRegistered(userId);
        } catch (error) {
            setMessage({ text: error.message, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2 style={{ marginBottom: '20px', color: '#667eea' }}>계정 설정</h2>
            
            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            <div className="form-group">
                <label htmlFor="userId">사용자 ID</label>
                <input type="text" id="userId" placeholder="회사 사용자 ID" value={formData.userId} onChange={handleChange} required />
            </div>
            
            <div className="form-group">
                <label htmlFor="password">비밀번호</label>
                <input type="password" id="password" placeholder="회사 비밀번호" value={formData.password} onChange={handleChange} required />
            </div>

            <div className="form-group">
                <label htmlFor="floorNm">배달 층</label>
                <input type="text" id="floorNm" placeholder="예: 5층" value={formData.floorNm} onChange={handleChange} required />
            </div>

            <div className="form-group">
                <label>메뉴 선호 순서 (드래그하여 변경)</label>
                <MenuPreferenceSelector 
                    value={formData.menuSeq}
                    onChange={handleMenuSeqChange}
                />
            </div>
            
            <button onClick={handleRegister} disabled={loading}>
                {loading ? '처리 중...' : '등록 완료'}
            </button>
        </div>
    );
}
