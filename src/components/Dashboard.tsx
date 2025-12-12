import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  LogOut, 
  Upload, 
  Loader2, 
  CheckCircle, 
  Sparkles,
  FileText,
  BarChart3
} from 'lucide-react';
import { FileUpload } from './FileUpload';
import { Results } from './Results';
import { apiClient, Transaction } from '@/lib/api';

interface DashboardProps {
  onLogout: () => void;
}

type ProcessingState = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

interface ProcessingData {
  sessionId: string;
  filename: string;
  format_type: string;
  total_amount: number;
  transaction_count: number;
  totals: Record<string, number>;
  date_range: {
    min_date: string;
    max_date: string;
  };
  transactions: Transaction[];
}

export function Dashboard({ onLogout }: DashboardProps) {
  const [state, setState] = useState<ProcessingState>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [processingData, setProcessingData] = useState<ProcessingData | null>(null);

  const handleUploadComplete = async (sessionId: string, filename: string) => {
    setState('processing');
    setProgress(0);
    setError('');

    try {
      // Simulate processing progress
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 5, 90));
      }, 200);

      const result = await apiClient.processPdf(sessionId);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      setProcessingData({
        sessionId,
        filename,
        ...result
      });
      
      setTimeout(() => {
        setState('completed');
      }, 500);
      
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Ошибка обработки файла');
      setProgress(0);
    }
  };

  const handleStartOver = () => {
    setState('idle');
    setProgress(0);
    setError('');
    setProcessingData(null);
  };

  const getStatusMessage = () => {
    switch (state) {
      case 'uploading':
        return 'Загружаем файл на сервер...';
      case 'processing':
        if (progress < 30) return '🔍 Анализируем формат PDF...';
        if (progress < 60) return '📊 Извлекаем транзакции...';
        if (progress < 90) return '🧮 Подсчитываем статистику...';
        return '✨ Финальные штрихи...';
      case 'completed':
        return '🎉 Анализ завершен успешно!';
      default:
        return '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Sparkles className="h-6 w-6 text-green-500" />
            <h1 className="text-xl font-bold text-white">SpendSense</h1>
            <span className="text-sm text-gray-400">Web Edition</span>
          </div>
          
          <div className="flex items-center space-x-4">
            {state === 'completed' && (
              <Button
                onClick={handleStartOver}
                variant="outline"
                size="sm"
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                <Upload className="mr-2 h-4 w-4" />
                Новый файл
              </Button>
            )}
            
            <Button
              onClick={onLogout}
              variant="outline"
              size="sm"
              className="border-gray-600 text-gray-300 hover:bg-gray-700"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Выйти
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {state === 'idle' && (
          <div className="space-y-6">
            {/* Welcome Card */}
            <Card className="bg-gray-800 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5 text-green-500" />
                  <span>Добро пожаловать в SpendSense</span>
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Онлайн версия для анализа банковских выписок. 
                  Поддерживаются оригинальный формат и RBC формат с автоматическим определением.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-300">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-blue-400" />
                    <span>Автоматическое определение формата</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="h-4 w-4 text-green-400" />
                    <span>Детальная аналитика</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Upload className="h-4 w-4 text-purple-400" />
                    <span>Экспорт в Excel и CSV</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* File Upload */}
            <FileUpload onUploadComplete={handleUploadComplete} />
          </div>
        )}

        {(state === 'uploading' || state === 'processing') && (
          <div className="max-w-2xl mx-auto">
            <Card className="bg-gray-800 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  <Loader2 className="h-5 w-5 animate-spin text-green-500" />
                  <span>Обработка файла</span>
                </CardTitle>
                <CardDescription className="text-gray-400">
                  {processingData?.filename && `Файл: ${processingData.filename}`}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Progress value={progress} className="w-full" />
                <div className="text-center">
                  <p className="text-green-400 font-medium">{getStatusMessage()}</p>
                  <p className="text-sm text-gray-500 mt-1">{progress}% завершено</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {state === 'error' && (
          <div className="max-w-2xl mx-auto">
            <Alert className="bg-red-900 border-red-700">
              <AlertDescription className="text-red-300">
                {error}
              </AlertDescription>
            </Alert>
            
            <div className="mt-4 text-center">
              <Button
                onClick={handleStartOver}
                className="bg-green-600 hover:bg-green-700"
              >
                Попробовать снова
              </Button>
            </div>
          </div>
        )}

        {state === 'completed' && processingData && (
          <div className="space-y-6">
            {/* Success Message */}
            <Card className="bg-green-900 border-green-700">
              <CardContent className="p-4">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="h-6 w-6 text-green-400" />
                  <div>
                    <p className="text-green-100 font-medium">
                      Файл успешно обработан!
                    </p>
                    <p className="text-green-200 text-sm">
                      Найдено {processingData.transaction_count} транзакций в формате{' '}
                      {processingData.format_type === 'original' ? 'Оригинальный' : 'RBC'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Results */}
            <Results sessionId={processingData.sessionId} data={processingData} />
          </div>
        )}
      </main>
    </div>
  );
}