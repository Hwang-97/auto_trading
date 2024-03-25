import store from '@/store';
export default async function beforeEach(to, from, next) {
  console.log("=====beforeEach=====");
  console.log("to   : ",to);
  console.log("from : ",from);
  console.log("next : ",next);
  console.log("=====beforeEach=====");
  // to 라우트가 인증이 필요한 경우
  const ip = '클라이언트 아이피'; // 실제 IP 주소로 설정
  const token = '유효한 JWT 토큰'; // 실제 JWT 토큰으로 설정

  const isValid = await store.dispatch('auth/checkAuthentication', { ip, token });

  if (isValid) {
    // 인증 유효한 경우
    next();
  } else {
    // 인증 유효하지 않은 경우
    next('/login');
  }
}