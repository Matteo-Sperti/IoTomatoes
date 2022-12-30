import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import xgboost as xgb
from sklearn.metrics import mean_squared_error

class Consumption_Algorithm:
    def __init__(self):
        self.reg = None
    
    def create_features(df):
        """
        Create time series features based on time series index.
        """
        df = df.copy()
        df['hour'] = df.index.hour
        df['dayofweek'] = df.index.dayofweek
        df['quarter'] = df.index.quarter
        df['month'] = df.index.month
        df['year'] = df.index.year
        df['dayofyear'] = df.index.dayofyear
        df['dayofmonth'] = df.index.day
        df['weekofyear'] = df.index.isocalendar().week
        return df

    def train_model(self):
        """ Train the model using as input the updated training data """

        df = pd.read_csv('input/PJME_hourly.csv')
        df = df.set_index('Datetime')
        df.index = pd.to_datetime(df.index)

        train = df.loc[df.index < '01-01-2015']
        test = df.loc[df.index >= '01-01-2015']

        df = self.create_features(df)

        train = self.create_features(train)
        test = self.create_features(test)

        FEATURES = ['dayofyear', 'hour', 'dayofweek', 'quarter', 'month', 'year']
        TARGET = 'PJME_MW'

        X_train = train[FEATURES]
        Y_train = train[TARGET]

        X_test = test[FEATURES]
        Y_test = test[TARGET]

        self.reg = xgb.XGBRegressor(base_score=0.5, booster='gbtree',    
                       n_estimators=500,
                       early_stopping_rounds=50,
                       objective='reg:linear',
                       max_depth=5,
                       subsample=0.8,
                       learning_rate=0.01)

        self.reg.fit(X_train, Y_train, eval_set=[(X_train, Y_train), (X_test, Y_test)], verbose=200)
        print('Train RMSE: %.3f' % mean_squared_error(Y_train, self.reg.predict(X_train))**0.5)

        test['prediction'] = self.reg.predict(X_test)
        df = df.merge(test[['prediction']], how='left', left_index=True, right_index=True)

        score = np.sqrt(mean_squared_error(test['PJME_MW'], test['prediction']))
        print(f'Test RMSE: {score:0.3f}')

        test['error'] = np.abs(test[TARGET] - test['prediction'])
        test['date'] = test.index.date
        
    def predict_data(self, final_date):
        """ Predict the data until the selected date """
        
        df = pd.read_csv('input/PJME_hourly.csv')
        df.sort_values(by='Datetime', inplace=True)

        initial_date = df['Datetime'].iat[-1]
        df = df[:-1]
        
        df = df.set_index('Datetime')
        df.index = pd.to_datetime(df.index)

        try:
            pred = pd.DataFrame()
            pred['Datetime'] = pd.date_range(start=initial_date, end=final_date, freq="1h")
            pred = pred.set_index('Datetime')
            pred.index = pd.to_datetime(pred.index)
            
            df = self.create_features(df)
            pred = self.create_features(pred)

            FEATURES = ['dayofyear', 'hour', 'dayofweek', 'quarter', 'month', 'year']
            X_pred = pred[FEATURES]

            pred['prediction'] = self.reg.predict(X_pred)
            df = pd.concat([df, pred])

            df_output = df[['PJME_MW'], ['prediction']]

            df_output.to_csv(f'DataPrediction_{final_date}.csv')

            ax = df[['PJME_MW']].plot(figsize=(15, 5))
            pred['prediction'].plot(ax=ax)
            plt.legend(['Truth Data', 'Predictions'])
            ax.set_title('Raw Dat and Prediction')
            plt.show()

        except ValueError:
            print('Error: The final date must be greater than the initial date')



if __name__ == '__main__':

    model = Consumption_Algorithm()
    model.train_model()

    while(input('New prediction?') == 'y'):
        final_date = input('Enter the final date for the prediction (YYYY-MM-DD): ')        
        model.predict_data(final_date)


        
        