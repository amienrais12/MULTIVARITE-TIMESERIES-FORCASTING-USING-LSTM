# -*- coding: utf-8 -*-
"""Copy of amienrais_skripsi_lstm.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Z2otKDGReXktK6rXB2-gOATuT7-FzK6L
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# %matplotlib inline
import seaborn as sns
sns.set_theme(style="whitegrid")
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv('slr.csv')
df.head(10)

"""Melihat informasi singkat dari dataframe"""

df.info()

"""Dari informasi singkat di atas, kita dapat mengetahui bahwa df terdiri dari 1409 baris.
Selain itu, pada kolom Datetime, tipe datanya masih berupa object (String) sehingga perlu diubah menjadi tipe data datetime dengan cara berikut.
"""

# merubah tipe data object to datetime
df['Time'] = df['Time'].astype('datetime64[ns]')

# melihat tipe data dataframe
print(df.dtypes)

df.head(30)

print('waktu terawal dari kolom Datetime adalah:', df['Time'].min())
df.head()

# mengurutkan data berdasarkan waktu
df.sort_values('Time', inplace=True, ignore_index=True)
df.head()

plt.figure(figsize=(15,8))
sns.lineplot(data=df, x='Time', y='SLR')

"""Memilih Data Setahun Terakhir
Pada contoh ini kita hanya akan gunakan data setahun terakhir dari data SLR
Karena data yang diobservasi per HARI, maka kita akan mengambil Sample sebanyak 365 baris terakhir dari df dan dimasukan kedalam variabel df1

"""

df1 = df[-2*365:].reset_index(drop=True)
df1.head()

plt.figure(figsize=(15,8))
sns.lineplot(data=df1, x='Time', y='SLR')

"""Melihat Statistika Deskriptif dari Data
Sebelum melakukan pembuatan model, sebaiknya dilakukan analisa terhadap statistika deskriptif dari data
Dari statistika deskriptif tersebut, kita dapat meilhat range dari data dan ukuran pusat data

"""

df1.describe()

"""Dari statistika deskriptif di atas terlihat bahwa data SLR minus dan berada pada range-87 dan 194 sehingga nanti kita akan lakukan feature scalling menggunakan MinMaxScaler agar range dari seluruh data tersebut berada di antara 0 dan 1

"""

from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose

result=seasonal_decompose(df['SLR'], model='additive', period=365)

result.plot()

"""bisa kita lihat bahwa data memiiki tingakat seasonal yang tinggi dan berulang dengan trend yang relativ sama"""

def dickey_fuller(series,title='Your Dataset'):
    '''Hypothesis Test for stationarity '''
    print(f'Augmented Dickey Fuller Test for the dataset {title}')
    
    result = adfuller(series.dropna(),autolag='AIC')
    labels = ['ADF test statistics','p-value','#lags','#observations'] # use help(adfuller) to understand why these labels are chosen
    
    outcome = pd.Series(result[0:4],index=labels)
    
    for key,val in result[4].items():
        outcome[f'critical value ({key})'] = val
        
    print(outcome.to_string()) # this will not print the line 'dtype:float64'
    
    if result[1] <= 0.05:
        print('Strong evidence against the null hypothesis') # Ho is Data is not stationary, check help(adfuller)
        print('Reject the null hypothesis')
        print('Data is Stationary')
    else:
        print('Weak evidence against the Null hypothesis')
        print('Fail to reject the null hypothesis')
        print('Data has a unit root and is non stationary')

dickey_fuller(df['SLR'],title='SLR')

"""Kita lihat data yang akan ddigunakan untuk pemodelan sudah stasioner, maka dari itu data aman untuk dilanjutnkan ke proses modeling

#Check Stasionaritas sangat penting untuk melakukan forcasting dan merupakan kewajiban utama sebelum melakukan modeling untuk mengetahui apakah data stassioner atau tidak

### Split Data


Split data dilakukan agar model yang telah dilatih dapat dievaluasi kemampuannya.
Karena data yang digunakan adalah data time series, maka split data tidak dilakukan secara acak
Kita juga akan melakukan cross validation menggunakan data train sehingga pastikan data train yang digunakan cukup besar.
Pada contoh ini kita gunakan 70% baris pertama sebagai data train dan 30% sisanya sebagai data test.
"""

# split data
train_size = int(len(df1) * 0.7) # Menentukan banyaknya data train yaitu sebesar 70% data
train = df1[:train_size]
test =df1[train_size:].reset_index(drop=True)

"""Feature Scalling Menggunakan MinMaxScaler
MinMaxScaler difit pada data train agar dapat digunakan kembali pada data test maupun data observasi baru.
Hasil scalling disimpan pada kolom baru yaitu 'scaled'

"""

from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
scaler.fit(train[['SLR']])

train['scaled'] = scaler.transform(train[['SLR']])
test['scaled'] = scaler.transform(test[['SLR']])

"""Mari kita lihat 5 data pertama pada data train untuk melihat data yang sudah discalling"""

train.head()

"""Membuat fungsi sliding window
Selanjutnya kita akan membuat fungsi sliding window dengan input data (bertipe data numpy array) dan window size
Fungsi ini akan menghasilkan variabel input (X) dan variabel target (y)
"""

def sliding_window(data, window_size):
    sub_seq, next_values = [], []
    for i in range(len(data)-window_size):
        sub_seq.append(data[i:i+window_size])
        next_values.append(data[i+window_size])
    X = np.stack(sub_seq)
    y = np.array(next_values)
    return X,y

"""Berapa window size yang tepat untuk digunakan?
Pada penerapannya kita dapat menentukan window size berapa saja.
Untuk mencapai hasil yang maksimal dapat dilakukan percobaan dengan menggunakan beberapa window size.
Perlu diperhatikan juga bahwa semakin** besar window size **yang digunakan akan memerlukan waktu yang cukup lama dalam proses training data
Pada contoh ini kita hanya menggunakan window size = 24 atau sama dengan 1 hari dan kita terapkan pada data train dan test yang telah discalling
"""

window_size = 24

X_train, y_train = sliding_window(train[['scaled']].values, window_size)
X_test, y_test = sliding_window(test[['scaled']].values, window_size)

print(X_train.shape, y_train.shape)
print(X_test.shape, y_test.shape)

"""Penting!!!
Data input LSTM harus 3D : [samples, timesteps, feature]

## LSTM menggunakan Tensorflow dan Keras


Untuk membuat LSTM() layer menggunakan Keras, perhatikan parameter-parameter berikut untuk membuat LSTM layer sederhana, ada beberapa parameter yaitu 


*   units: menentukan banyaknya LSTM unit
*   input_shape: menentukan ukuran timesteps dan feature, diperlukan pada layer pertama
*   return_sequences: jika layer berikutnya berupa LSTM layer maka return_sequences=True (default = False)

# Membuat Model Forecasting Menggunakan LSTM

Untuk menggunakan arsitektur GRU, ganti model LSTM dengan RNN atau GRU
"""

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM #, RNN, GRU

"""# 2. Membuat Fungsi Model Forecasting Menggunakan LSTM
Fungsi model yang akan dibuat terdiri:

LSTM layer dengan 
* input_shape = (window_size, 1)
* Dense layer dengan 32 neuron dengan fungsi aktivasi ReLu
* Dropout antara Dense layer dan Dense output layer
* Dense output layer dengan 1 neuron
* loss function yang digunakan adalah Mean Squared Error (MSE)
* optimizer yang digunakan adalah adam
* metric yang digunakan adalah Mean Absolute Error (MAE)

* Parameter-parameter yang dijadikan sebagai input dari fungsi tersebut adalah:
  - LSTM_unit: banyaknya LSTM unit (default = 64)
  - dropout: persentase dropout (default = 0.2)
"""

def create_model(LSTM_unit=64, dropout=0.2): #jika ingin menggunakan RNN atau GRU ganti LSTM dengan GRU/RNN
    # create model
    model = Sequential()
    model.add(LSTM(units=LSTM_unit, input_shape=(window_size, 1)))
    model.add(Dense(32, activation='relu'))
    model.add(Dropout(dropout))
    model.add(Dense(1))
    # Compile model
    model.compile(loss='mse', optimizer='adam', metrics=['mae'])
    return model

"""#3. Membuat Model
Kita coba lakukan hypertuning pada parameter, dengan mencoba kombinasi nilai LSTM unitnya 16,32,64,28 dan peluang dropout 0,1 dan 0,2


"""

LSTM_unit = [16,32,64,128]
dropout = [0.1,0.2]

"""Selain itu, kita juga gunakan early stopping pada saat proses training


"""

from sklearn.model_selection import GridSearchCV
from keras.wrappers.scikit_learn import KerasRegressor
from keras.callbacks import EarlyStopping
# Early Stopping
es = EarlyStopping(monitor = 'val_loss', mode = "min", patience = 5, verbose = 0)

# create model
model = KerasRegressor(build_fn=create_model, epochs=150, validation_split=0.1, batch_size=32, callbacks=[es], verbose=1)

# define the grid search parameters
LSTM_unit = [16,32,64,128]
dropout=[0.1,0.2]
param_grid = dict(LSTM_unit=LSTM_unit, dropout=dropout)

"""# 4. Membuat Variabel GridSearchCV
Variabel GridSearchCV dibuat dengan memasukan beberapa parameter yaitu:
- estimator: model yang ingin dilakukan gridsearch
- param_grid: parameter yang ingin diuji
- n_jobs: Jumlah pekerjaan untuk dijalankan secara paralel. (-1 artinya menggunakan seluruh core processor)
- cv: banyaknya k-fold cross validation
"""

grid = GridSearchCV(estimator=model, param_grid=param_grid, n_jobs=-1, cv=5)

grid_result = grid.fit(X_train, y_train)

"""Mengecek hasil parametrik"""

# summarize results
print("Best: %f using %s" % (grid_result.best_score_, grid_result.best_params_))
means = grid_result.cv_results_['mean_test_score']
stds = grid_result.cv_results_['std_test_score']
params = grid_result.cv_results_['params']
for mean, stdev, param in zip(means, stds, params):
    print("%f (%f) with: %r" % (mean, stdev, param))
    
# Mengambil model terbaik
best_model = grid_result.best_estimator_.model

"""Dari Hasil Training menggunakan GridSearchCV, kita peroleh:

parameter terbaiknya adalah: {'LSTM_unit': 64, 'dropout': 0.1}
Rata-rata Loss Function dari hasil Cross Validation adalah 0.000353
Kemudian coba kita lihat grafik loss function MSE dan metric MAE terhadap epoch untuk melihat performa model terbaik kita dengan cara sebagai berikut

Kita dapat melihat grafik loss function MSE dan metric MAE terhadap epoch untuk melihat performa model kita dengan cara sebagai berikut

"""

history = best_model.history
# grafik loss function MSE

plt.plot(history.history['loss'], label='Training loss')
plt.plot(history.history['val_loss'], label='Validation loss')
plt.title('loss function MSE')
plt.ylabel('MSE')
plt.xlabel('Epoch')
plt.legend()

# grafik metric MAE

plt.plot(history.history['mae'], label='Training MAE')
plt.plot(history.history['val_mae'], label='Validation MAE')
plt.title('metric MAE')
plt.ylabel('MAE')
plt.xlabel('Epoch')
plt.legend()

"""# Model Evaluaation"""

# Prediksi data train
predict_train = scaler.inverse_transform(best_model.predict(X_train))
true_train = scaler.inverse_transform(y_train)

# Prediksi data test
predict_test = scaler.inverse_transform(best_model.predict(X_test))
true_test = scaler.inverse_transform(y_test)

train['predict'] = np.nan
train['predict'][-len(predict_train):] = predict_train[:,0]

plt.figure(figsize=(15,8))
sns.lineplot(data=train, x='Time', y='SLR', label = 'train')
sns.lineplot(data=train, x='Time', y='predict', label = 'predict')

# pLOT PREDIKSI DATSET

test['predict'] = np.nan
test['predict'][-len(predict_test):] = predict_test[:,0]

plt.figure(figsize=(15,8))
sns.lineplot(data=test, x='Time', y='SLR', label = 'test')
sns.lineplot(data=test, x='Time', y='predict', label = 'predict')

#Plot prediksi sebulan terakhir
plt.figure(figsize=(15,8))
sns.lineplot(data=test[-24*30:], x='Time', y='SLR', label = 'test')
sns.lineplot(data=test[-24*30:], x='Time', y='predict', label = 'predict')

# forecasting data selanjutnya
y_test = scaler.transform(test[['SLR']])
n_future = 24*7
future = [[y_test[-1,0]]]
X_new = y_test[-window_size:,0].tolist()

for i in range(n_future):
    y_future = best_model.predict(np.array([X_new]).reshape(1,window_size,1))
    future.append([y_future[0,0]])
    X_new = X_new[1:]
    X_new.append(y_future[0,0])

future = scaler.inverse_transform(np.array(future))
date_future = pd.date_range(start=test['Time'].values[-1], periods=n_future+1, freq='H')
# Plot Data sebulan terakhir dan seminggu ke depan
plt.figure(figsize=(15,8))
sns.lineplot(data=test[-24*30:], x='Time', y='SLR', label = 'test')
sns.lineplot(data=test[-24*30:], x='Time', y='predict', label = 'predict')
sns.lineplot(x=date_future, y=future[:,0], label = 'future')
plt.ylabel('SLR');