"""
Setup script for DinDin Quant Bot.

This allows the package to be installed in development mode:
    pip install -e .
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / 'README.md'
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ''

setup(
    name='dindin-quant-bot',
    version='1.0.0',
    description='Professional quantitative trading bot for Taiwan stock market',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='DinDin',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/DinDin_Quant_Bot',
    
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    
    python_requires='>=3.10',
    
    install_requires=[
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'yfinance>=0.2.0',
        'backtesting>=0.3.3',
        'bokeh==2.4.3',
        'plotly>=5.0.0',
        'streamlit>=1.28.0',
        'PyYAML>=6.0',
        'python-dateutil>=2.8.0',
    ],
    
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'shioaji': [
            'shioaji>=1.0.0',
        ],
    },
    
    entry_points={
        'console_scripts': [
            'dindin-dashboard=presentation.dashboard.app:main',
            'dindin-setup-db=scripts.setup_db:main',
            'dindin-fetch-data=scripts.fetch_historical_data:main',
        ],
    },
    
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial :: Investment',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    
    keywords='trading quantitative finance taiwan stock-market algorithmic-trading',
)
