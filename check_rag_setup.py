#!/usr/bin/env python3
"""
RAG系统依赖检查和初始化脚本
检查RAG功能所需的依赖、配置和环境设置
"""

import os
import sys
import subprocess
import importlib
import logging
from typing import Dict, List, Tuple, Any
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGSetupChecker:
    """RAG设置检查器"""
    
    def __init__(self):
        self.required_packages = [
            'chromadb',
            'sentence-transformers',
            'numpy',
            'pandas',
            'torch',
            'transformers',
            'dashscope',
            'python-dotenv'
        ]
        
        self.optional_packages = [
            'faiss-cpu',
            'scikit-learn',
            'matplotlib',
            'seaborn'
        ]
        
        self.required_directories = [
            './data',
            './data/knowledge_base',
            './data/knowledge_base/vectors',
            './logs'
        ]
        
        self.required_env_vars = [
            'DASHSCOPE_API_KEY',
            'RAG_ENABLED',
            'RAG_SIMILARITY_THRESHOLD',
            'RAG_CONFIDENCE_THRESHOLD'
        ]
        
        self.check_results = {
            'packages': {},
            'directories': {},
            'environment': {},
            'configuration': {},
            'services': {}
        }
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的RAG设置检查"""
        logger.info("开始RAG系统设置检查...")
        
        # 检查Python包依赖
        self._check_packages()
        
        # 检查目录结构
        self._check_directories()
        
        # 检查环境变量
        self._check_environment()
        
        # 检查配置文件
        self._check_configuration()
        
        # 检查服务可用性
        self._check_services()
        
        # 生成检查报告
        return self._generate_report()
    
    def _check_packages(self):
        """检查Python包依赖"""
        logger.info("检查Python包依赖...")
        
        # 检查必需包
        for package in self.required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                self.check_results['packages'][package] = {
                    'status': 'installed',
                    'required': True,
                    'version': self._get_package_version(package)
                }
                logger.info(f"✓ {package} 已安装")
            except ImportError:
                self.check_results['packages'][package] = {
                    'status': 'missing',
                    'required': True,
                    'version': None
                }
                logger.error(f"✗ {package} 未安装")
        
        # 检查可选包
        for package in self.optional_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                self.check_results['packages'][package] = {
                    'status': 'installed',
                    'required': False,
                    'version': self._get_package_version(package)
                }
                logger.info(f"✓ {package} 已安装 (可选)")
            except ImportError:
                self.check_results['packages'][package] = {
                    'status': 'missing',
                    'required': False,
                    'version': None
                }
                logger.warning(f"- {package} 未安装 (可选)")
    
    def _check_directories(self):
        """检查目录结构"""
        logger.info("检查目录结构...")
        
        for directory in self.required_directories:
            path = Path(directory)
            if path.exists() and path.is_dir():
                self.check_results['directories'][directory] = {
                    'status': 'exists',
                    'writable': os.access(path, os.W_OK),
                    'size': self._get_directory_size(path)
                }
                logger.info(f"✓ 目录 {directory} 存在")
            else:
                self.check_results['directories'][directory] = {
                    'status': 'missing',
                    'writable': False,
                    'size': 0
                }
                logger.warning(f"- 目录 {directory} 不存在")
    
    def _check_environment(self):
        """检查环境变量"""
        logger.info("检查环境变量...")
        
        # 加载.env文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.warning("python-dotenv未安装，无法加载.env文件")
        
        for env_var in self.required_env_vars:
            value = os.getenv(env_var)
            if value:
                self.check_results['environment'][env_var] = {
                    'status': 'set',
                    'value': value if env_var != 'DASHSCOPE_API_KEY' else '***masked***'
                }
                logger.info(f"✓ 环境变量 {env_var} 已设置")
            else:
                self.check_results['environment'][env_var] = {
                    'status': 'missing',
                    'value': None
                }
                logger.error(f"✗ 环境变量 {env_var} 未设置")
    
    def _check_configuration(self):
        """检查配置文件"""
        logger.info("检查配置文件...")
        
        # 检查.env文件
        env_file = Path('.env')
        if env_file.exists():
            self.check_results['configuration']['.env'] = {
                'status': 'exists',
                'readable': os.access(env_file, os.R_OK),
                'size': env_file.stat().st_size
            }
            logger.info("✓ .env文件存在")
        else:
            self.check_results['configuration']['.env'] = {
                'status': 'missing',
                'readable': False,
                'size': 0
            }
            logger.error("✗ .env文件不存在")
        
        # 检查配置模块
        try:
            from chatbi.config import config
            validation_result = config.validate()
            self.check_results['configuration']['config_validation'] = {
                'status': 'valid' if validation_result['valid'] else 'invalid',
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings']
            }
            
            if validation_result['valid']:
                logger.info("✓ 配置验证通过")
            else:
                logger.error(f"✗ 配置验证失败: {validation_result['errors']}")
                
        except Exception as e:
            self.check_results['configuration']['config_validation'] = {
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"✗ 配置加载失败: {e}")
    
    def _check_services(self):
        """检查服务可用性"""
        logger.info("检查服务可用性...")
        
        # 检查DashScope API
        try:
            import dashscope
            api_key = os.getenv('DASHSCOPE_API_KEY')
            if api_key:
                # 简单的API测试
                dashscope.api_key = api_key
                self.check_results['services']['dashscope'] = {
                    'status': 'available',
                    'api_key_set': True
                }
                logger.info("✓ DashScope API可用")
            else:
                self.check_results['services']['dashscope'] = {
                    'status': 'unavailable',
                    'api_key_set': False,
                    'error': 'API密钥未设置'
                }
                logger.error("✗ DashScope API密钥未设置")
        except ImportError:
            self.check_results['services']['dashscope'] = {
                'status': 'unavailable',
                'error': 'dashscope包未安装'
            }
            logger.error("✗ dashscope包未安装")
        except Exception as e:
            self.check_results['services']['dashscope'] = {
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"✗ DashScope API检查失败: {e}")
        
        # 检查ChromaDB
        try:
            import chromadb
            # 尝试创建临时客户端
            client = chromadb.Client()
            self.check_results['services']['chromadb'] = {
                'status': 'available',
                'version': chromadb.__version__ if hasattr(chromadb, '__version__') else 'unknown'
            }
            logger.info("✓ ChromaDB可用")
        except ImportError:
            self.check_results['services']['chromadb'] = {
                'status': 'unavailable',
                'error': 'chromadb包未安装'
            }
            logger.error("✗ chromadb包未安装")
        except Exception as e:
            self.check_results['services']['chromadb'] = {
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"✗ ChromaDB检查失败: {e}")
    
    def _get_package_version(self, package_name: str) -> str:
        """获取包版本"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def _get_directory_size(self, path: Path) -> int:
        """获取目录大小"""
        try:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        # 统计结果
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        warnings = 0
        
        # 统计包检查结果
        for package, result in self.check_results['packages'].items():
            total_checks += 1
            if result['status'] == 'installed':
                passed_checks += 1
            elif result['required']:
                failed_checks += 1
            else:
                warnings += 1
        
        # 统计目录检查结果
        for directory, result in self.check_results['directories'].items():
            total_checks += 1
            if result['status'] == 'exists':
                passed_checks += 1
            else:
                failed_checks += 1
        
        # 统计环境变量检查结果
        for env_var, result in self.check_results['environment'].items():
            total_checks += 1
            if result['status'] == 'set':
                passed_checks += 1
            else:
                failed_checks += 1
        
        # 统计配置检查结果
        config_validation = self.check_results['configuration'].get('config_validation', {})
        if config_validation.get('status') == 'valid':
            passed_checks += 1
        else:
            failed_checks += 1
        total_checks += 1
        
        # 统计服务检查结果
        for service, result in self.check_results['services'].items():
            total_checks += 1
            if result['status'] == 'available':
                passed_checks += 1
            else:
                failed_checks += 1
        
        # 生成报告
        report = {
            'summary': {
                'total_checks': total_checks,
                'passed': passed_checks,
                'failed': failed_checks,
                'warnings': warnings,
                'success_rate': (passed_checks / total_checks * 100) if total_checks > 0 else 0
            },
            'details': self.check_results,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 检查缺失的必需包
        missing_required = [
            pkg for pkg, result in self.check_results['packages'].items()
            if result['required'] and result['status'] == 'missing'
        ]
        
        if missing_required:
            recommendations.append(
                f"安装缺失的必需包: pip install {' '.join(missing_required)}"
            )
        
        # 检查缺失的目录
        missing_dirs = [
            dir_path for dir_path, result in self.check_results['directories'].items()
            if result['status'] == 'missing'
        ]
        
        if missing_dirs:
            recommendations.append(
                f"创建缺失的目录: mkdir -p {' '.join(missing_dirs)}"
            )
        
        # 检查缺失的环境变量
        missing_env = [
            env_var for env_var, result in self.check_results['environment'].items()
            if result['status'] == 'missing'
        ]
        
        if missing_env:
            recommendations.append(
                f"在.env文件中设置环境变量: {', '.join(missing_env)}"
            )
        
        # 检查配置问题
        config_validation = self.check_results['configuration'].get('config_validation', {})
        if config_validation.get('status') != 'valid':
            if config_validation.get('errors'):
                recommendations.append(
                    f"修复配置错误: {'; '.join(config_validation['errors'])}"
                )
        
        return recommendations
    
    def auto_fix(self) -> bool:
        """自动修复可修复的问题"""
        logger.info("开始自动修复...")
        
        success = True
        
        # 创建缺失的目录
        for directory, result in self.check_results['directories'].items():
            if result['status'] == 'missing':
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"✓ 创建目录: {directory}")
                except Exception as e:
                    logger.error(f"✗ 创建目录失败 {directory}: {e}")
                    success = False
        
        # 尝试安装缺失的必需包
        missing_required = [
            pkg for pkg, result in self.check_results['packages'].items()
            if result['required'] and result['status'] == 'missing'
        ]
        
        if missing_required:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install'
                ] + missing_required, check=True)
                logger.info(f"✓ 安装包: {', '.join(missing_required)}")
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 安装包失败: {e}")
                success = False
        
        return success


def main():
    """主函数"""
    checker = RAGSetupChecker()
    
    # 运行检查
    report = checker.run_full_check()
    
    # 打印报告
    print("\n" + "="*60)
    print("RAG系统设置检查报告")
    print("="*60)
    
    summary = report['summary']
    print(f"总检查项: {summary['total_checks']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"警告: {summary['warnings']}")
    print(f"成功率: {summary['success_rate']:.1f}%")
    
    if report['recommendations']:
        print("\n修复建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # 询问是否自动修复
    if summary['failed'] > 0:
        try:
            response = input("\n是否尝试自动修复可修复的问题? (y/N): ")
            if response.lower() in ['y', 'yes']:
                if checker.auto_fix():
                    print("✓ 自动修复完成")
                    # 重新检查
                    print("\n重新检查...")
                    new_report = checker.run_full_check()
                    new_summary = new_report['summary']
                    print(f"修复后成功率: {new_summary['success_rate']:.1f}%")
                else:
                    print("✗ 自动修复部分失败，请手动处理")
        except KeyboardInterrupt:
            print("\n用户取消")
    
    # 保存详细报告
    try:
        import json
        report_file = f"./data/rag_setup_report_{os.getpid()}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n详细报告已保存到: {report_file}")
    except Exception as e:
        logger.warning(f"保存报告失败: {e}")
    
    # 返回退出码
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())