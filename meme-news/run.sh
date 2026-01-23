#!/bin/bash

# MemeNews 실행 스크립트
# 사용법: ./run.sh [command]
#   start   - 서비스 시작
#   stop    - 서비스 중지
#   restart - 서비스 재시작
#   logs    - 로그 보기
#   build   - 이미지 빌드
#   shell   - 컨테이너 쉘 접속

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
print_logo() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════╗"
    echo "║         🎭 MemeNews v1.0.0           ║"
    echo "║    자동 밈 콘텐츠 생성 시스템       ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

# 환경 확인
check_requirements() {
    echo -e "${YELLOW}[*] 환경 확인 중...${NC}"

    # Docker 확인
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[!] Docker가 설치되어 있지 않습니다.${NC}"
        echo "    설치: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Docker Compose 확인
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}[!] Docker Compose가 설치되어 있지 않습니다.${NC}"
        exit 1
    fi

    echo -e "${GREEN}[✓] 환경 확인 완료${NC}"
}

# 디렉토리 생성
setup_directories() {
    echo -e "${YELLOW}[*] 디렉토리 설정 중...${NC}"

    mkdir -p data output/images output/videos logs config

    echo -e "${GREEN}[✓] 디렉토리 설정 완료${NC}"
}

# 환경 변수 파일 생성
setup_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}[*] .env 파일 생성 중...${NC}"
        cat > .env << 'EOF'
# MemeNews 환경 설정
# 이 파일을 수정하거나 Admin 페이지에서 설정하세요

# 보안 키 (변경 필수!)
SECRET_KEY=change_me_in_production_use_random_string

# 관리자 계정 (첫 실행 시 사용)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=memenews123!

# 타임존
TZ=Asia/Seoul

# API 키 (Admin 페이지에서 설정 가능)
# GEMINI_API_KEY=
# YOUTUBE_CLIENT_ID=
# YOUTUBE_CLIENT_SECRET=
# YOUTUBE_REFRESH_TOKEN=
EOF
        echo -e "${GREEN}[✓] .env 파일 생성 완료${NC}"
        echo -e "${YELLOW}[!] .env 파일의 SECRET_KEY를 변경하세요!${NC}"
    fi
}

# Docker Compose 명령 실행
docker_compose() {
    if docker compose version &> /dev/null; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

# 서비스 시작
start() {
    echo -e "${YELLOW}[*] MemeNews 시작 중...${NC}"

    check_requirements
    setup_directories
    setup_env

    docker_compose up -d --build

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     🎉 MemeNews가 시작되었습니다!    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Admin 페이지: ${BLUE}http://localhost:8000${NC}"
    echo ""
    echo -e "  기본 계정"
    echo -e "  - ID: ${YELLOW}admin${NC}"
    echo -e "  - PW: ${YELLOW}memenews123!${NC}"
    echo ""
    echo -e "${RED}  ⚠️  보안을 위해 비밀번호를 변경하세요!${NC}"
    echo ""
}

# 서비스 중지
stop() {
    echo -e "${YELLOW}[*] MemeNews 중지 중...${NC}"
    docker_compose down
    echo -e "${GREEN}[✓] MemeNews가 중지되었습니다.${NC}"
}

# 서비스 재시작
restart() {
    stop
    start
}

# 로그 보기
logs() {
    docker_compose logs -f
}

# 이미지 빌드
build() {
    echo -e "${YELLOW}[*] Docker 이미지 빌드 중...${NC}"
    docker_compose build --no-cache
    echo -e "${GREEN}[✓] 빌드 완료${NC}"
}

# 컨테이너 쉘 접속
shell() {
    docker_compose exec memenews /bin/bash
}

# 상태 확인
status() {
    echo -e "${YELLOW}[*] 서비스 상태${NC}"
    docker_compose ps
}

# 도움말
help() {
    print_logo
    echo "사용법: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start     서비스 시작 (기본)"
    echo "  stop      서비스 중지"
    echo "  restart   서비스 재시작"
    echo "  logs      로그 보기"
    echo "  build     Docker 이미지 빌드"
    echo "  shell     컨테이너 쉘 접속"
    echo "  status    서비스 상태 확인"
    echo "  help      도움말"
    echo ""
}

# 메인
main() {
    print_logo

    case "${1:-start}" in
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        logs)
            logs
            ;;
        build)
            build
            ;;
        shell)
            shell
            ;;
        status)
            status
            ;;
        help|--help|-h)
            help
            ;;
        *)
            echo -e "${RED}[!] 알 수 없는 명령: $1${NC}"
            help
            exit 1
            ;;
    esac
}

main "$@"
